"""Read raw article events from Kafka, extract entities, and publish counts."""

import logging
import sys
from pathlib import Path
from datetime import datetime

import spacy
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col,
    coalesce,
    concat_ws,
    current_timestamp,
    explode,
    from_json,
    lit,
    struct,
    to_json,
    to_timestamp,
    udf,
    window,
)
from pyspark.sql.types import (
    ArrayType,
    IntegerType,
    StringType,
    StructField,
    StructType,
)

# Allow `python spark/entity_stream.py` to import repo-root modules.
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config import KAFKA_BOOTSTRAP, NER_MODEL, SLIDE_DURATION, WINDOW_DURATION

# Why two topics?
# `raw-articles` is the durable ingestion topic and `entity-counts` is the
# processed analytics topic. Keeping them separate means the producer can
# continue writing raw events even if Spark is down, and the stream can be
# replayed from Kafka offsets without re-calling the news API.

# Configure logging
LOG_DIR = ROOT_DIR / "spark" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / f"entity_stream_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

RAW_ARTICLES_TOPIC = "raw-articles"
ENTITY_COUNTS_TOPIC = "entity-counts"
ALLOWED_ENTITY_TYPES = {"ORG", "PERSON", "GPE", "PRODUCT"}
KAFKA_PACKAGE = "org.apache.spark:spark-sql-kafka-0-10_2.13:4.1.1"
FETCHED_AT_FORMAT = "yyyy-MM-dd'T'HH:mm:ssX"
_NLP = None

RAW_ARTICLE_SCHEMA = StructType(
    [
        StructField("event_id", StringType(), False),
        StructField("source", StringType(), False),
        StructField("fetched_at", StringType(), False),
        StructField("headline", StringType(), False),
        StructField("body", StringType(), True),
        StructField("url", StringType(), False),
        StructField("category", StringType(), False),
    ]
)

ENTITY_RESULT_SCHEMA = ArrayType(
    StructType(
        [
            StructField("entity", StringType(), False),
            StructField("entity_type", StringType(), False),
        ]
    )
)

def normalize_entity(text: str) -> str:
    """Collapse whitespace and apply a stable title-case normalization."""
    if not text:
        return ""
    cleaned = " ".join(text.split()).strip()
    return cleaned.title() if cleaned else ""


def extract_entities(text: str):
    """Extract only the entity types the downstream schema supports."""
    global _NLP

    try:
        if not text or not text.strip():
            return []

        if _NLP is None:
            # Each Python worker loads spaCy lazily the first time the UDF runs.
            # This avoids fragile function-serialization patterns on Spark.
            _NLP = spacy.load(NER_MODEL)

        # Bound the text chunk processed per event so one unusually long article
        # does not dominate worker memory or latency.
        doc = _NLP(text[:1000])
        entities = []
        seen = set()
        
        for ent in doc.ents:
            if ent.label_ not in ALLOWED_ENTITY_TYPES:
                continue

            normalized = normalize_entity(ent.text)
            if not normalized:
                continue

            entity_key = (normalized, ent.label_)
            if entity_key in seen:
                continue

            seen.add(entity_key)
            entities.append({"entity": normalized, "entity_type": ent.label_})

        return entities
    except Exception as e:
        logger.error(f"Error extracting entities: {e}")
        return []


extract_entities_udf = udf(extract_entities, ENTITY_RESULT_SCHEMA)


def build_spark_session() -> SparkSession:
    """Create the Spark session with the Kafka connector attached."""
    logger.info("Creating Spark session with Kafka package %s", KAFKA_PACKAGE)
    spark = (
        SparkSession.builder
        .appName("EntityStream")
        .master("local[1]")
        .config("spark.jars.packages", KAFKA_PACKAGE)
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .config("spark.local.hostname", "127.0.0.1")
        .config("spark.network.timeout", "300s")
        .config("spark.executor.heartbeatInterval", "60s")
        .config("spark.rpc.askTimeout", "300s")
        .config("spark.driver.memory", "2g")
        .config("spark.executor.memory", "2g")
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.shuffle.service.enabled", "false")
        .config("spark.hadoop.io.native.lib.available", "false")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    return spark


def build_stream(spark: SparkSession):
    """Construct the full streaming transformation graph."""
    logger.info("Connecting to Kafka bootstrap servers: %s", KAFKA_BOOTSTRAP)

    kafka_df = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP)
        .option("subscribe", RAW_ARTICLES_TOPIC)
        .option("startingOffsets", "latest")
        .option("failOnDataLoss", "false")
        .load()
    )

    parsed_df = (
        kafka_df.selectExpr("CAST(value AS STRING) AS raw_value")
        .select(from_json(col("raw_value"), RAW_ARTICLE_SCHEMA).alias("article"))
        .filter(col("article").isNotNull())
        .select("article.*")
        .withColumn("fetched_at_ts", to_timestamp(col("fetched_at"), FETCHED_AT_FORMAT))
        .filter(col("fetched_at_ts").isNotNull())
        .withColumn(
            "content",
            concat_ws(" ", col("headline"), coalesce(col("body"), lit(""))),
        )
        .withColumn("entities", extract_entities_udf(col("content")))
    )

    exploded_df = (
        parsed_df.withColumn("entity_record", explode(col("entities")))
        .select(
            col("fetched_at_ts"),
            col("entity_record.entity").alias("entity"),
            col("entity_record.entity_type").alias("entity_type"),
        )
    )

    aggregated_df = (
        exploded_df.withWatermark("fetched_at_ts", WINDOW_DURATION)
        .groupBy(
            window(col("fetched_at_ts"), WINDOW_DURATION, SLIDE_DURATION),
            col("entity"),
            col("entity_type"),
        )
        .count()
        .select(
            col("window.start").cast("string").alias("window_start"),
            col("window.end").cast("string").alias("window_end"),
            col("entity"),
            col("entity_type"),
            col("count").cast(IntegerType()).alias("count"),
            current_timestamp().cast("string").alias("trigger_at"),
        )
    )

    kafka_output_df = aggregated_df.select(
        lit(ENTITY_COUNTS_TOPIC).alias("topic"),
        to_json(
            struct(
                col("window_start"),
                col("window_end"),
                col("entity"),
                col("entity_type"),
                col("count"),
                col("trigger_at"),
            )
        ).alias("value"),
    )

    logger.info("Stream graph built successfully")
    return kafka_output_df


def main() -> None:
    """Main entry point with exception handling and graceful shutdown."""
    spark = None
    query = None
    
    try:
        logger.info("Starting EntityStream application")
        logger.info("Writing application logs to %s", LOG_FILE)
        spark = build_spark_session()
        logger.info("Spark session created successfully")
        
        stream_df = build_stream(spark)
        logger.info("Building streaming query")
        
        query = (
            stream_df.writeStream.format("kafka")
            .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP)
            # This query is stateful; checkpoint reuse matters for restartability.
            .option("checkpointLocation", str(ROOT_DIR / "spark" / "checkpoints" / "entity_stream"))
            .outputMode("append")
            .start()
        )
        
        logger.info("Streaming query started. Waiting for data...")
        logger.info(
            "Checkpoint directory: %s",
            ROOT_DIR / "spark" / "checkpoints" / "entity_stream",
        )
        
        query.awaitTermination()
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
    finally:
        if query is not None:
            try:
                logger.info("Stopping streaming query")
                query.stop()
                query.awaitTermination(timeout=30)
            except Exception as e:
                logger.error(f"Error stopping query: {e}")
        
        if spark is not None:
            try:
                logger.info("Stopping Spark session")
                spark.stop()
            except Exception as e:
                logger.error(f"Error stopping Spark: {e}")
        
        logger.info("EntityStream application stopped")


if __name__ == "__main__":
    main()

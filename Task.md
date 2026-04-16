# Problem 1: Spark Streaming with Real Time Data and Kafka

In this part, you will create a Spark Streaming application that continuously reads text data from a real-time source, analyzes the text for named entities, and sends their counts to Apache Kafka. A pipeline using Elasticsearch and Kibana will read the data from Kafka and analyze it visually. 

## Setting up your development environment

You can set up everything on your local machine or host them on the cloud. Following are the resources that you will need:

* You will need to get access to a real-time text data source. Some examples are:

  * Finnhub

    * Can be used for financial news and analysis.
    * Website: [https://finnhub.io/](https://finnhub.io/)
    * Python wrapper: [https://pypi.org/project/finnhub-python/](https://pypi.org/project/finnhub-python/)

* Download Apache Kafka and go through the quickstart steps:

  * [https://kafka.apache.org/quickstart](https://kafka.apache.org/quickstart)

* Windows users might want to consider WSL, which gives a Unix-like environment on Windows:

  * [https://docs.microsoft.com/en-us/windows/wsl/install-win10](https://docs.microsoft.com/en-us/windows/wsl/install-win10)

* You will need a working Spark cluster.

  * It can be set up locally or on a cloud server.

* A simple project showing how to pass data between Kafka and a Spark Structured Streaming application that performs word count has been attached.

* Later, you will also need to set up Elasticsearch and Kibana to visualize data.

  * Download Elasticsearch, Kibana, and Logstash from:

    * [https://www.elastic.co/downloads/](https://www.elastic.co/downloads/) 

## Project Steps

For this project, you will need to perform the following steps:

1. Create a Python application that reads from a real-time data source, such as Reddit, NewsAPI, or Finnhub.

   * Some libraries have a streaming version that continuously fetches real-time data.
   * Others may require writing a loop that fetches data periodically.

2. Continuously write the incoming data to a Kafka topic.

   * Example topic name: `topic1`

3. Create a PySpark Structured Streaming application that continuously reads data from the Kafka topic (`topic1`) and keeps a running count of named entities being mentioned.

   * You should extract named entities from the incoming text.
   * Keep a running count of entity mentions over time.

4. At each trigger interval, send a message containing the named entities and their counts to another Kafka topic.

   * Example topic name: `topic2`

5. Configure Logstash, Elasticsearch, and Kibana to read from Kafka topic `topic2`.

6. Create a bar plot in Kibana showing the top 10 most frequent named entities and their counts. 

## Visualizing the data using Elasticsearch and Kibana

You will need Elasticsearch and Kibana installed to retrieve data from Kafka and visualize it.

Useful resources:

* [https://www.elastic.co/downloads](https://www.elastic.co/downloads)
* [https://www.elastic.co/docs/get-started](https://www.elastic.co/docs/get-started)

You should visualize the top 10 named entities being mentioned in your chosen data source using a bar plot in Kibana. 

## End Goal
MAKE IT PUBLISHABLE

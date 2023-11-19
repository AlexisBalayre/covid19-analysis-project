# COVID-19 Data Analysis Project

## Overview 🌍

This project harnesses Big Data and Machine Learning technologies to analyse the global impact of the COVID-19 pandemic. Utilising Apache Spark, it processes extensive datasets of COVID-19 cases, uncovering insights into the virus's spread and effects.

## Key Features 🌟

- **Automated Data Ingestion**: Fetches and stores the latest COVID-19 data automatically.
- **Advanced Query Analysis**: Employs complex queries for analysing average daily cases, weekly statistical trends, and clustering in heavily affected regions.
- **Performance Optimisation**: Implements Spark best practices for efficient data processing.
- **Ethical Consideration Analysis**: Addresses crucial aspects of privacy and ethical technology use.

## Getting Started 🚀

### Installation

1. **Clone the repository**:

   ```bash
   git clone git@github.com:AlexisBalayre/cranfield-assessment-2.git
   ```

2. **Enter the project directory**:

   ```bash
   cd Covid19AnalysisProject
   ```

3. **Create a virtual environment**:

   ```bash
   python3 -m venv venv
   ```

4. **Activate the virtual environment**:

   - On Windows:

   ```bash
   .\venv\Scripts\activate
   ```

   - On Unix or MacOS:

     ```bash
     source venv/bin/activate
     ```

5. **Install required libraries**:

   ```bash
   pip install -r requirements.txt
   ```

### Usage

- **Run the analysis**: Execute `main.py` to start the data processing.

  ```bash
  python main.py
  ```

- **Visualise the results**: Open `visualisation.ipynb` in Jupyter Notebook for interactive visualisations.

## Project Structure 📂

- `Covid19AnalysisProjectLib/`: Core library modules.
- `dags/`: Scheduling tasks with Apache Airflow.
- `data/`: Datasets and geographical boundary files.
- `results/`: Storage for analysis outputs and visualisations.
- `main.py`: Primary script for running the analysis.
- `visualisation.ipynb`: Jupyter Notebook for result visualisation.

## Dependencies 🛠️

- Apache Spark
- Python 3.x
- Pandas, GeoPandas
- Seaborn, Matplotlib
- Apache Airflow (optional, for task scheduling)

#!/bin/bash


mkdir -p requirements

cat <<EOL > requirements/agents.txt
requests==2.32.3
python-dotenv==1.0.1

# Optionnel (scraping)
beautifulsoup4==4.13.4
EOL

cat <<EOL > requirements/pipeline.txt
numpy==1.26.4
pandas==2.2.2
scikit-learn==1.5.1
xgboost==2.0.3
mlxtend==0.23.1
EOL

cat <<EOL > requirements/dashboard.txt
streamlit==1.37.0
plotly==5.22.0
pandas==2.2.2

langchain-core==0.2.38
langchain-google-genai==1.0.10
langchain-groq==0.1.9
EOL

echo "done !"
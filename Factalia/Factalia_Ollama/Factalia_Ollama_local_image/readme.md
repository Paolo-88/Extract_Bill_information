# Overview

This script is designed to extract specific information from PDF files containing invoices. Below is a summary of its functionality and the libraries it uses.

# Libraries
os
re
csv
requests
paddleocr
pdf2image
numpy
shutil

# Functionality

Convert PDF to Images: The script converts the PDF into images.
Extract Text from Images: It then extracts text from these images.
Text Segmentation: If the text is too long, it is segmented into manageable parts.
First Query to LLaMA: The text is organized into sections using LLaMA.
Second Query to LLaMA: Only the necessary information is extracted through a second query to LLaMA.
Write and Save Information: The extracted information is written to and saved in a CSV file.

# Fact-Alia Openai - Google Drive version
Script python to extract precise information from bills in a Gogole Drive Folder and  upload it neatly to a csv file in a shared folder always on Google Drive.



## Usage



1. Dependency Installation

2. Make sure you have all the necessary libraries installed

3. Replace the OpenAI API key in the code with your personal key.
 
4.To connect to Google Drive folders, you need to obtain a file called "credentials.json," which should be placed in the same directory as the script. This file contains all the permissions required to connect to Google's APIs.

How to obtain it:

4.1 Go to the Google Cloud Console.
4.2 Click on Select a Project (or Create Project if you don't have one yet).
4.3 Enter a name for your project and select a location.
4.4 Click on Create.
4.5 In the Google Cloud Console, select the newly created project.
4.6 Go to APIs & Services > Library.
4.7 Search for Google Drive API and click on it.
4.8 Click on Enable to activate the API.
4.9 After enabling the API, go to APIs & Services > Credentials.
4.10 Click on Create Credentials and select Service Account.
4.11 Fill in the required details
4.12 Click on Continue.
4.13 Download JSON  file. The file contain the service account credentials. This file will contain the information needed to access the APIs (save it in the same folder of the script)
4.14 Go to Google Drive and find the folder or file you want to access.
4.15 Right-click on the folder/file and select Share.
4.15 Enter the email address of the service account you found in the JSON file (it should have a format like your-service-account@your-project-id.iam.gserviceaccount.com).
4.16 Grant the necessary permissions (Editor)
4.17 do the same with csv folder

5. You can run the script
















Configurazione di Google Drive con le credenziali json

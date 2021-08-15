# CENOS

## What it does
If you highlight text on a page then click on the Chrome Extension, enter the category, and press submits, it automatically adds to/updates your Google Doc with the text you highlighted (linking the source) under the category you specified. Then once you have all your notes, on the Chrome Extension you can press the summarize button, and it will automatically add a summary of each section (created by a machine learning algorithm) to the bottom.

## How I built it
I used HTML, JS, and CSS for the chrome extension and python (Flask) for the backend. I began with Flask and setting up the Google Docs API so I could access a document from my drive. Then I created the Chrome Extension and worked on passing information between the two.

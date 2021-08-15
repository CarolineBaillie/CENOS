import os
import flask
from flask import request, redirect, url_for, render_template
import json
from cs50 import SQL
import httplib2
from googleapiclient import discovery
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage
from googleapiclient.discovery import build
import webbrowser
from transformers import pipeline

app = flask.Flask(__name__)

# Page built off of example from https://prahladyeri.com/blog/2016/12/how-to-create-google-drive-app-python-flask.html

#config db
db = SQL("sqlite:///data/lamp.db")
# config ml model - used from https://towardsdatascience.com/abstractive-summarization-using-pytorch-f5063e67510
summarizer = pipeline("summarization", model="t5-base", tokenizer="t5-base", framework="tf")

@app.route('/', methods=['GET','POST'])
def index():
    doc_url = 'https://docs.google.com/document/d/11xf-0E96T4f1AANFf0lNmgC4PojdPXGA-s70xRfYmgM/edit'
    if request.method == "GET": # test case
        credentials = get_credentials()
        if credentials == False:
            return flask.redirect(flask.url_for('oauth2callback'))
        elif credentials.access_token_expired:
            return flask.redirect(flask.url_for('oauth2callback'))
        else:
            #DO STUFF IN DRIVE
            append_new_stuff()
            return render_template("loggedIn.html", doc_url=doc_url)
    if request.method == "POST":
        # get info from frontend
        resp = json.loads(request.data)
        info = resp['info']
        cat = resp['cat']
        link = resp['tabUrl']
        # clean data
        cat = cat.lower()
        cat = cat[0].upper() + cat[1:]
        info = info.replace('\n','')
        info = info.replace('\xa0','')
        info = info.replace('\t','')
        info = info.replace('\r','')
        # save in DB
        db.execute("INSERT INTO notes (type, info, link) VALUES (:type, :info, :link)",
                       type=cat, info=info, link=link)
        # make sure authorized
        credentials = get_credentials()
        if credentials == False:
            webbrowser.open_new_tab('http://127.0.0.1:5000/')
        elif credentials.access_token_expired:
            webbrowser.open_new_tab('http://127.0.0.1:5000/')
        else:
            #DO STUFF IN DRIVE
            append_new_stuff()
            return render_template("loggedIn.html", doc_url=doc_url)

@app.route('/sum', methods=['GET','POST'])
def summarize():
    credentials = get_credentials()
    if credentials == False:
        webbrowser.open_new_tab('http://127.0.0.1:5000/')
    elif credentials.access_token_expired:
        webbrowser.open_new_tab('http://127.0.0.1:5000/')
    else:
        #DO STUFF IN DRIVE
        get_contents_of_page()
        print("done")
        return "working"
        
@app.route('/oauth2callback')
def oauth2callback():
    flow = client.flow_from_clientsecrets('client_secret.json',
            scope='https://www.googleapis.com/auth/drive',
            redirect_uri=flask.url_for('oauth2callback', _external=True)) # access drive api using developer credentials
    flow.params['include_granted_scopes'] = 'true'
    if 'code' not in flask.request.args:
        auth_uri = flow.step1_get_authorize_url()
        return flask.redirect(auth_uri)
    else:
        auth_code = flask.request.args.get('code')
        credentials = flow.step2_exchange(auth_code)
        open('credentials.json','w').write(credentials.to_json()) # write access token to credentials.json locally 
        return flask.redirect(flask.url_for('index'))

def append_new_stuff():
    # define stuff
    DOCUMENT_ID = '11xf-0E96T4f1AANFf0lNmgC4PojdPXGA-s70xRfYmgM'
    creds = get_credentials()
    service = build('docs', 'v1', credentials=creds)
    requests = []
    # delete everything so far
    document = service.documents().get(documentId=DOCUMENT_ID).execute()
    body = document['body']
    content = body['content']
    temp = content[len(content)-1]
    endIndex = temp['endIndex']
    if endIndex != 2: # safety case
        requests.append({
            'deleteContentRange': {
                'range': {
                    'startIndex': 1,
                    'endIndex': endIndex-1,
                }
            }
        })
    # get values from db
    all_notes = db.execute("SELECT * FROM notes ORDER BY id DESC")
    all_types = db.execute("SELECT DISTINCT type FROM notes")
    #TESTING
    # all_types = ['How\n','What\n']
    # all_notes = ['this is one thing *\n','this is another bullet *\n', 'the final bullet to see if deleted *\n']
    # add to document
    requests.append({
        'deleteParagraphBullets': {
            'range': {
                "segmentId": "",
                "startIndex": 1,
                "endIndex": 1
            }
        }
    })
    for i in range(0,len(all_types)):
        for n in all_notes:
            if n['type'] == all_types[i]['type']:
                # add asteric and \n
                n['info'] = n['info'] + ' *\n'
                type = all_types[i]['type'] + '\n'
                requests.append({
                    'insertText': {
                        'location': {
                            'index': 1,
                        },
                        'text': n['info']
                    }
                })
                requests.append({
                    'updateTextStyle': {
                        'range': {
                            'startIndex': 1,
                            'endIndex': len(n['info'])-1
                        },
                        'textStyle': {
                            'underline': False
                        },
                        'fields': 'underline'
                    }
                })
                requests.append({
                    'updateTextStyle': {
                        'range': {
                            'startIndex': len(n['info'])-1,
                            'endIndex': len(n['info'])
                        },
                        'textStyle': {
                            'link': {
                                'url': n['link']
                            }
                        },
                        'fields': 'link'
                    }
                })
                requests.append({
                    'createParagraphBullets': {
                        "range": {
                            "segmentId": "",
                            "startIndex": 1,
                            "endIndex": 1
                        },
                        "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE"
                    }
                })
        requests.append({
            'insertText': {
                'location': {
                    'index': 1,
                },
                'text': type
            }
        })
        requests.append({
            'deleteParagraphBullets': {
                'range': {
                    "segmentId": "",
                    "startIndex": 1,
                    "endIndex": 1
                }
            }
        })
        requests.append({
            'updateTextStyle': {
                'range': {
                    'startIndex': 1,
                    'endIndex': len(type)
                },
                'textStyle': {
                    'underline': True
                },
                'fields': 'underline'
            }
        })
    if(requests != []):
        result = service.documents().batchUpdate(documentId=DOCUMENT_ID, body={'requests': requests}).execute()
    return "worked"

def get_contents_of_page():
    DOCUMENT_ID = '11xf-0E96T4f1AANFf0lNmgC4PojdPXGA-s70xRfYmgM'
    creds = get_credentials()
    service = build('docs', 'v1', credentials=creds)
    document = service.documents().get(documentId=DOCUMENT_ID).execute()
    total = []
    section = ""
    for i in range(0,len(document.get('body')['content'])):
        try:
            text = document.get('body')['content'][i]['paragraph']['elements'][0]['textRun']['content']
            if text[-1] != '\n':
                # later add . if not there?
                section = section + text
            else:
                total.append(section)
                section = ""
        except:
            print("not there")
    total = total[1:]
    summerized = []
    for t in total:
        summary_text = summarizer(t, max_length=100, min_length=5, do_sample=False)[0]['summary_text']
        summerized.append(summary_text)
    reload_page(summerized)
    return "working"

def reload_page(summerized):
    print(summerized)
    # define stuff
    DOCUMENT_ID = '11xf-0E96T4f1AANFf0lNmgC4PojdPXGA-s70xRfYmgM'
    creds = get_credentials()
    service = build('docs', 'v1', credentials=creds)
    requests = []
    # delete everything so far
    document = service.documents().get(documentId=DOCUMENT_ID).execute()
    body = document['body']
    content = body['content']
    temp = content[len(content)-1]
    endIndex = temp['endIndex']
    if endIndex != 2: # safety case
        requests.append({
            'deleteContentRange': {
                'range': {
                    'startIndex': 1,
                    'endIndex': endIndex-1,
                }
            }
        })
    # get values from db
    all_notes = db.execute("SELECT * FROM notes ORDER BY id DESC")
    all_types = db.execute("SELECT DISTINCT type FROM notes")
    #add summaries
    # add to document
    for i in range(0,len(all_types)):
        l = len(all_types) - 1
        s = "Summary: " + summerized[l-i] + "\n \n"
        requests.append({
            'insertText': {
                'location': {
                    'index': 1,
                },
                'text': s
            }
        })
        requests.append({
            'updateTextStyle': {
                'range': {
                    'startIndex': 1,
                    'endIndex': len(summerized[l-i])+10
                },
                'textStyle': {
                    'underline': False
                },
                'fields': 'underline'
            }
        })
        requests.append({
            'deleteParagraphBullets': {
                'range': {
                    "segmentId": "",
                    "startIndex": 1,
                    "endIndex": 1
                }
            }
        })
        for n in all_notes:
            if n['type'] == all_types[i]['type']:
                # add asteric and \n
                n['info'] = n['info'] + ' *\n'
                type = all_types[i]['type'] + '\n'
                requests.append({
                    'insertText': {
                        'location': {
                            'index': 1,
                        },
                        'text': n['info']
                    }
                })
                # requests.append({
                #     'updateTextStyle': {
                #         'range': {
                #             'startIndex': 1,
                #             'endIndex': len(n['info'])-1
                #         },
                #         'textStyle': {
                #             'underline': False
                #         },
                #         'fields': 'underline'
                #     }
                # })
                requests.append({
                    'updateTextStyle': {
                        'range': {
                            'startIndex': len(n['info'])-1,
                            'endIndex': len(n['info'])
                        },
                        'textStyle': {
                            'link': {
                                'url': n['link']
                            }
                        },
                        'fields': 'link'
                    }
                })
                requests.append({
                    'createParagraphBullets': {
                        "range": {
                            "segmentId": "",
                            "startIndex": 1,
                            "endIndex": 1
                        },
                        "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE"
                    }
                })
        requests.append({
            'insertText': {
                'location': {
                    'index': 1,
                },
                'text': type
            }
        })
        requests.append({
            'deleteParagraphBullets': {
                'range': {
                    "segmentId": "",
                    "startIndex": 1,
                    "endIndex": 1
                }
            }
        })
        requests.append({
            'updateTextStyle': {
                'range': {
                    'startIndex': 1,
                    'endIndex': len(type)
                },
                'textStyle': {
                    'underline': True
                },
                'fields': 'underline'
            }
        })
    if(requests != []):
        result = service.documents().batchUpdate(documentId=DOCUMENT_ID, body={'requests': requests}).execute()
    return "worked"


def get_credentials():
    credential_path = 'credentials.json'

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        print("Credentials not found.")
        return False
    else:
        print("Credentials fetched successfully.")
        return credentials

def fetch(query, sort='modifiedTime desc'):
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v3', http=http)
    results = service.files().list(
        q=query,orderBy=sort,pageSize=10,fields="nextPageToken, files(id, name)").execute()
    items = results.get('files', [])
    return items

def download_file(file_id, output_file):
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v3', http=http)
    #file_id = '0BwwA4oUTeiV1UVNwOHItT0xfa2M'
    request = service.files().export_media(fileId=file_id,mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    #request = service.files().get_media(fileId=file_id)
    
    fh = open(output_file,'wb') #io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
        #print ("Download %d%%." % int(status.progress() * 100))
    fh.close()
    #return fh
    
def update_file(file_id, local_file):
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v3', http=http)
    # First retrieve the file from the API.
    file = service.files().get(fileId=file_id).execute()
    # File's new content.
    media_body = MediaFileUpload(local_file, resumable=True)
    # Send the request to the API.
    updated_file = service.files().update(
        fileId=file_id,
        #body=file,
        #newRevision=True,
        media_body=media_body).execute()

        
if __name__ == '__main__':
    if os.path.exists('client_secret.json') == False:
        print('Client secrets file (client_secret.json) not found in the app path.')
        exit()
    import uuid
    app.secret_key = str(uuid.uuid4())
    app.run(debug=True)
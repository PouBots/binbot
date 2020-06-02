import requests 
import json

class reqs:
    
    def __init__():
        """Nothing to do yet"""
        
    def _get(url, params=None, headers=None):
        """ Makes a Get Request """
        try: 
            response    = requests.get(url, params=params, headers=headers)
            data        = json.loads(response.text)
        except Exception as e:
            raise Exception
            print("Exception occured when trying to get from " + url)
            print(e)
            data = {'code': '-1', 'url':url, 'msg': e}
        return data

    def _post(url, params=None, headers=None):
        """ Makes a Post Request """
        try: 
            response    = requests.post(url, params=params, headers=headers)
            data        = json.loads(response.text)
        except Exception as e:
            print("Exception occured when trying to post to " + url)
            print(e)
            data = {'code': '-1', 'url':url, 'msg': e}
        return data

    def _delete(url, params=None, headers=None):
        """ Makes a delete Request """
        try: 
            response    = requests.delete(url, params=params, headers=headers)
            data        = json.loads(response.text)
        except Exception as e:
            print("Exception occured when trying to delete on " + url)
            print(e)
            data = {'code': '-1', 'msg':e}
        return data

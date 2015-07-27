import base64
import datetime
import hashlib
import json
import requests
import urllib
import urlparse


CREATE_USER_API_URL = '/api/user/create'
VERIFY_USER_API_URL = '/api/user/checkUsername'
EDIT_USER_API_URL = '/api/user/edit'
DELETE_USER_API_URL = '/api/user/delete'

class DoceboSSO(object):

  def initialize_keys(self, domain, api_secret, api_key, sso_secret):
    self.domain = domain
    self.api_secret = api_secret
    self.api_key = api_key
    self.sso_secret = sso_secret

  def create_datestring(self):
    """Creates datestring in format asked for by Docebo"""
    currentDatetime = datetime.datetime.now()
    datestring = currentDatetime.strftime('%Y%m%d%H%M%S')
    return datestring

  def create_token(self, username, datestring):
    """Creates MD5 hashed sso_token for Docebo SSO

    Args:
     username: Current user's email
     sso_secret: The sso token provided by Docebo
     datestring: Timestamp generated by create_datestring
    Returns:
      Valid hashed SSO token
    """
    token_hash = hashlib.md5()
    token_hash.update(username + ',')
    token_hash.update(datestring + ',')
    token_hash.update(self.sso_secret)
    sso_token = token_hash.hexdigest()
    return sso_token

  def create_authentication_path(self, username, datestring, token):
    """Returns path to Docebo SSO endpoint, with all necessary params.

    Args:
     self.domain: Current user's email
     username: Email of current user
     datestring: Timestamp generated by create_datestring
     token: Valid hashed SSO token
    Returns:
      Valid signed SSO URL
    """

    location = self.domain + '/doceboLms/index.php'
    params = {
      'modname': 'login',
      'op': 'confirm',
      'login_user': username.lower(),
      'time': datestring,
      'token': token
    }

    # Return the modified redirect URL.
    return location + '?' + urllib.urlencode(params)

  def setup_valid_sso_path_and_params(self, username):
    """SSO into users account

    Args:
     user: User model representing current user
     self.domain: netloc to redirect user to to SSO
    Returns:
      Valid signed SSO URL
    """
    #username = self.get_username_from_email(user.user_id)
    datestring = self.create_datestring()
    ssoToken = self.create_token(username, datestring)
    redirect_path = self.create_authentication_path(username, datestring, ssoToken)
    self.send_request_to_docebo(redirect_path, {})
    return redirect_path

  def generate_api_hash(self, params):
    """Generate hash from params and API secret necessary for making Docebo API calls.

    Args:
     params: params of the API call to be made
    Returns:
      valid API hash
    """
    param_string = ','.join(params.values())
    secret_hash = hashlib.sha1(param_string + ',' + self.api_secret)
    auth_token = base64.b64encode(self.api_key + ':' + secret_hash.hexdigest())
    return auth_token


  def send_request_to_docebo(self, api_url, params):
    """Setup and send request to Docebo given URL and params

    Args:
     api_url: URL to perform given API function
     params: parameters for API request
    Returns:
      JSON body of response
    Throws:
      400 error if Docebo cannot resolve request
    """
    headers = {'X-Authorization:': self.generate_api_hash(params)}
    data = urllib.urlencode(params)
    response = requests.request(
        "POST",
        url=api_url,
        data=params,
        headers=headers
      )
    response_json = response.content
    if response.status_code > 299:
      return requests.Response.raise_for_status()
    try:
      return json.loads(response_json)
    except:
      return None

  def generate_api_url(self, api_url):
    """append function specific API url to base domain"""
    api_url = urlparse.urljoin(self.domain, api_url)
    return api_url

  def verify_user(self, params):
    """Make Docebo API call to verify user.

    Args:
     user: user model for current user
    Returns:
      Body of response from API request
    """
    api_url = self.generate_api_url(VERIFY_USER_API_URL)
    response = self.send_request_to_docebo(api_url, params)
    return response

  def edit_user(self, params):
    """Send Docebo API request to update user info.

    Args:
     user: user model for current user
     docebo_user_id: numerical unique account id provided by Docebo
    Returns:
      Body of response from API request
    """
    api_url = self.generate_api_url(EDIT_USER_API_URL)
    response = self.send_request_to_docebo(api_url, params)
    return response

  def create_user(self, params):
    """Make Docebo API call to create user.

    Args:
     user: user model for current user
    Returns:
      Body of response from API request
    """
    api_url = self.generate_api_url(CREATE_USER_API_URL)
    response = self.send_request_to_docebo(api_url, params)
    return response

  def delete_user(self, params):
    """API call for user to be deleted -- useful for testing"""
    api_url = self.generate_api_url(DELETE_USER_API_URL)
    response = self.send_request_to_docebo(api_url, params)
    return response

  def get_username_from_email(self, user_email):
    """get email username (before the @) to use as Docebo username"""
    if user_email is None:
      return None
    split_email = user_email.split('@')[0]
    if split_email is None:
      return None
    return user_email.split('@')[0]
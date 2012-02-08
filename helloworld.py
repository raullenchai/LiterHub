import cgi
import datetime
import urllib2, urllib
import wsgiref.handlers
import re, os
import simplejson
import difflib
import sys 



from urllib2 import *
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import mail  

class Greeting(db.Model):
    """Data Model"""
    email = db.EmailProperty()
    title = db.StringProperty(multiline=True)
    add_date = db.DateTimeProperty(auto_now_add=True)
    tried = db.IntegerProperty(default=0)
    tried_date = db.DateTimeProperty(auto_now=True)
    url = db.StringProperty(default='NULL')

########################################UTILITIES#######################################################
def guestbook_key(guestbook_name=None):
    """Constructs a datastore key"""
    return db.Key.from_path('Guestbook', guestbook_name or 'default_guestbook')


def verify_reCAPTCHA (recaptcha_challenge_field,
            recaptcha_response_field,
            private_key,
            remoteip):
    """
    Submits a reCAPTCHA request for verification. Returns RecaptchaResponse
    for the request

    recaptcha_challenge_field -- The value of recaptcha_challenge_field from the form
    recaptcha_response_field -- The value of recaptcha_response_field from the form
    private_key -- your reCAPTCHA private key
    remoteip -- the user's ip address
    """

    if not (recaptcha_response_field and recaptcha_challenge_field and
            len (recaptcha_response_field) and len (recaptcha_challenge_field)):
        return RecaptchaResponse (is_valid = False, error_code = 'incorrect-captcha-sol')
    

    def encode_if_necessary(s):
        if isinstance(s, unicode):
            return s.encode('utf-8')
        return s

    params = urllib.urlencode ({
            'privatekey': encode_if_necessary(private_key),
            'remoteip' :  encode_if_necessary(remoteip),
            'challenge':  encode_if_necessary(recaptcha_challenge_field),
            'response' :  encode_if_necessary(recaptcha_response_field),
            })

    request = urllib2.Request (
        url = "http://www.google.com/recaptcha/api/verify",
        data = params,
        headers = {
            "Content-type": "application/x-www-form-urlencoded",
            "User-agent": "reCAPTCHA Python"
            }
        )
    
    httpresp = urllib2.urlopen (request)

    return_values = httpresp.read ().splitlines ();
    httpresp.close();
    return_code = return_values [0]

    if (return_code == "true"):
        return True
    else:
        return False


def search_google(word):
    #clean-up unicode characters
    output = ''
    for i in range(len(word)):
        if (word[i]>='0' and word[i]<='~') or word[i]<=' ':
            output += word[i]
        
    url = ('https://ajax.googleapis.com/ajax/services/search/web?v=1.0&q='+urllib.quote(cgi.escape(output))+'&userip=USERS-IP-ADDRESS')
    request = urllib2.Request(url, None, {'Referer': 'www.literhub.com'})
    response = urllib2.urlopen(request)
    return simplejson.load(response)
 
"""TODO:Search Bing"""

def is_online(url):
    """"test if the doc is online"""
    req = Request(cgi.escape(url))
    try: 
       reponse = urlopen(req)
    except HTTPError, e:
       url = None
       return False
    except URLError, e:
       url = None
       return False
    return True
   
 ##########################################################################################

class MainPage(webapp.RequestHandler):
    def get(self):
        self.response.out.write('<html><body>')
        guestbook_name='zzxc'

        self.response.out.write("""
                    <form action="/submit" method="POST">
                        <div><textarea name="email" rows="1" cols="60">raullenchai@gmail.com</textarea></div>
                        <div><textarea name="title" rows="3" cols="60">Designing Integrated Accelerator for Stream Ciphers with Structural Similarities</textarea></div>
                        <script type="text/javascript" src="http://www.google.com/recaptcha/api/challenge?k=6LfRJs0SAAAAAO9xDCduTjW5I9B19I5sBd6GkJqD"></script>
                        <noscript>
                          <iframe src="http://www.google.com/recaptcha/api/noscript?k=6LfRJs0SAAAAAO9xDCduTjW5I9B19I5sBd6GkJqD" height="300" width="500" frameborder="0"></iframe><br />
                          <textarea name="recaptcha_challenge_field" rows="3" cols="40"></textarea>
                          <input type='hidden' name='recaptcha_response_field' value='manual_challenge' />
                        </noscript>
                        <hr>
                        <div><input type="submit" value="Track It"></div>
                    </form>
                    """)
        self.response.out.write('</body></html>')
        


class AddPaper(webapp.RequestHandler):
    def post(self):
        guestbook_name = 'zzxc'

        if(len(self.request.get("recaptcha_response_field"))==0):
            self.response.out.write("""
                            <script type="text/javascript">
                            alert("Please use a valid CAPTCHA")
                            </script>""")

        #self.response.out.write('<blockquote>%s</blockquote>' % verify_reCAPTCHA (self.request.get("recaptcha_challenge_field"), self.request.get("recaptcha_response_field"), '6LfRJs0SAAAAAFpQxZ_NfEB6rI9AriZb6eUNQHui', os.environ["REMOTE_ADDR"]))
        elif( verify_reCAPTCHA (self.request.get("recaptcha_challenge_field"), self.request.get("recaptcha_response_field"), '6LfRJs0SAAAAAFpQxZ_NfEB6rI9AriZb6eUNQHui', os.environ["REMOTE_ADDR"])  ):
            
            greeting = Greeting(parent=guestbook_key(guestbook_name))
            greeting.email = cgi.escape(self.request.get('email'))
            greeting.title = cgi.escape(self.request.get('title'))
            
            flag = 0
            #If the email is valid
            if re.match("\w+([-+.']\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*", greeting.email):
                flag += 1
            
            #If the title is too short or too long, reject it
            if len(greeting.title)>8 and len(greeting.title)<300:
                flag += 2
    
            if flag == 3:
                #seems everthing is valid
                greeting.title = greeting.title.replace("\r\n", " ")
                greeting.put()
                self.response.out.write("""
                            <script type="text/javascript">
                            alert("You will be notified through email once this paper is available!")
                            </script>""")
            elif flag == 2:
                self.response.out.write("""
                            <script type="text/javascript">
                            alert("Please use a valid email")
                            </script>""")
            else:
                 self.response.out.write("""
                            <script type="text/javascript">
                            alert("Please use a valid title")
                            </script>""")

        self.response.out.write("""
                            <a href='/'>Start Over</a>""")
        #self.redirect('/' + urllib.urlencode({'guestbook_name': guestbook_name}))

class SearchPaper(webapp.RequestHandler):
  def get(self):
    greetings = Greeting.all()
    greetings.filter("url =", 'NULL')
    #greetings.order("-add_date")
        
    for greeting in greetings:
        self.response.out.write('<blockquote>%s</blockquote>' % cgi.escape(greeting.title))
        search_res = search_google(cgi.escape(greeting.title))
        found = False
        for x in search_res["responseData"]["results"]:
            seq=difflib.SequenceMatcher(a=cgi.escape(greeting.title).lower(), b=x["titleNoFormatting"].lower())
            if seq.ratio()>0.8 and is_online(x["url"]):
                found = True
                greeting.tried += 1
                greeting.url = x["url"]
                greeting.put()
                self.response.out.write('<blockquote>%s</blockquote>' % x["url"])

        if found==False:
            greeting.tried += 1
            greeting.put()


class SendEmail(webapp.RequestHandler):
  def get(self):
    greetings = db.GqlQuery("SELECT * FROM Greeting WHERE url != 'NULL'")

    for greeting in greetings:
        #self.response.out.write('<blockquote>%s</blockquote>' % cgi.escape(greeting.email))
        user_address = cgi.escape(greeting.email)
        
        if mail.is_email_valid(user_address) and greeting.tried>0:
            self.response.out.write('<blockquote>sending...</blockquote>')
            sender_address = 'raullenchai@literhub.com'
            subject = "Paper is Arrived"
            body = """
            Your paper entitled "%s" can be found through the following link: 
            """ % cgi.escape(greeting.title)
            
            body = body+"""%s. Enjoy!""" %cgi.escape(greeting.url)
            
            try:
                mail.send_mail(sender_address, user_address, subject, body)
                greeting.tried = -1 * greeting.tried
                greeting.put()
            except BadHeaderError:
                self.response.out.write('<blockquote>Error</blockquote>')

            self.response.out.write('<blockquote>done!</blockquote>')


"""
GAE is readonly, you can only store stuff in the datastore
class UpdateBG(webapp.RequestHandler):
    content=urllib2.urlopen('http://www.bing.com').read()
    result=re.search(r"g_img={url:'([^']*)",content)
    if result:
        result=result.groups(0)[0]
        result=result.replace('\\','')
        instream=urlopen('http://www.bing.com'+result)
        outfile=open('background.jpg','wb')
        for chunk in instream:
            outfile.write(chunk)
        instream.close()
        outfile.close()
"""


application = webapp.WSGIApplication([
    ('/', MainPage),
    ('/submit', AddPaper),
    ('/tasks/search', SearchPaper),
    ('/tasks/send', SendEmail),
], debug=True)



def main():
    run_wsgi_app(application)


if __name__ == '__main__':
    main()
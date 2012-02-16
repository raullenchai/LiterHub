
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

import defs

class Greeting(db.Model):
    """Data Model"""
    email = db.EmailProperty()
    title = db.StringProperty(multiline=True)
    add_date = db.DateTimeProperty(auto_now_add=True)
    tried = db.IntegerProperty(default=0)
    tried_date = db.DateTimeProperty(auto_now_add=True)
    url = db.StringProperty(default='NULL')

########################################Searching Functions#######################################################
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

 ##########################################################################################

class SearchPaper(webapp.RequestHandler):
  def get(self):
    greetings = Greeting.all()
    greetings.filter("url =", 'NULL')
    greetings.order("tried_date")
    #SELECT * FROM Greeting WHERE url = 'NULL' ORDER BY tried_date
    
    for greeting in greetings:        
        if greeting.tried_date > datetime.datetime.now():
            break
        self.response.out.write('<blockquote>%s</blockquote>' % cgi.escape(greeting.title))
        search_res = search_google(cgi.escape(greeting.title))
        found = False
        for x in search_res["responseData"]["results"]:
            #Here only to compare two title strings with the same lengths
            seq=difflib.SequenceMatcher(b = (cgi.escape(greeting.title).lower())[0:len(x["titleNoFormatting"].lower())]  , a = x["titleNoFormatting"].lower())
            #self.response.out.write('<blockquote>%f</blockquote>' % seq.ratio())
            if seq.ratio()>0.8:
                found = True
                greeting.tried += 1
                greeting.url = x["url"]
                greeting.put()
                self.response.out.write('<blockquote>%s</blockquote>' % x["url"])

        if found==False:
            greeting.tried += 1
            #next time to try: I don;t want some document will never be searched again if greeting.tried is too big....
            greeting.tried_date = datetime.datetime.now() + datetime.timedelta(hours=TIMING_FACTOR*(2**min(greeting.tried,8)))
            #that is saying maximumly after 1*2*8=256/24= 10 days, one paper will be checked again
            greeting.put()


class SendEmail(webapp.RequestHandler):
  def get(self):
    #greetings = db.GqlQuery("SELECT * FROM Greeting WHERE url != 'NULL'")
    greetings = Greeting.all()
    greetings.filter("url !=", 'NULL')
    
    for greeting in greetings:
        #self.response.out.write('<blockquote>%s</blockquote>' % cgi.escape(greeting.email))
        user_address = cgi.escape(greeting.email)
        
        if mail.is_email_valid(user_address) and greeting.tried>0:
            self.response.out.write('<blockquote>sending...</blockquote>')
            sender_address = 'noreply@literhub.com'
            subject = "Your Paper is Arrived!"
            body = """
            Your paper entitled "%s" is available here: 
            """ % cgi.escape(greeting.title)
            
            body = body+"""%s . 
            Enjoy!
            
            If our service is useful for you, a possible donation could start from here:
            https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=Y47PNDPZ2V4XY
            """ %cgi.escape(greeting.url)

            try:
                mail.send_mail(sender_address, user_address, subject, body)
                greeting.tried = -1 * greeting.tried
                greeting.put()
            except BadHeaderError:
                self.response.out.write('<blockquote>Error</blockquote>')

            self.response.out.write('<blockquote>done!</blockquote>')


#after running for a long period, the DB would be big and slow
#delete all entries such that the user of which has been notified
#this should only be called by admin
class CleanUp(webapp.RequestHandler):
  def get(self):
    greetings = Greeting.all()
    greetings.filter("url !=", 'NULL')
    
    for greeting in greetings:
        if greeting.tried<0:
            try:
                greeting.delete()
            except BadHeaderError:
                self.response.out.write('<blockquote>Error</blockquote>')

            self.response.out.write('<blockquote>done!</blockquote>')

    
class NotFound(webapp.RequestHandler):
  def get(self):    
    self.response.out.write("""
    <table border="0" cellspacing="0" cellpadding="0" width="100%" class="hit-layout">
    <tr>
    <td id="hit-a">
        <div class="hit-content">
        <h3>The Page You Requested Is Not Found</h3>
        <p> 
         <a href='/'>Start Over</a>
        </p>
        </div>
    </td>
    </tr>
    </table>
        
    """)


application = webapp.WSGIApplication([
    ('/admin/search', SearchPaper),
    ('/admin/send', SendEmail),
    ('/admin/clean', CleanUp),
    ('/admin/.*', NotFound),
], debug=True)


def main():
    run_wsgi_app(application)


if __name__ == '__main__':
    main()
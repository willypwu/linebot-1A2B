import webapp2
import handlers

app = webapp2.WSGIApplication([
    ('/', handlers.MainHandler),
    ('/callback', handlers.LinebotHandler),
], debug=True)

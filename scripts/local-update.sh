git pull
systemctl restart collect.service
systemctl restart post.service
journalctl -f -u collect -u post
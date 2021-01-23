python3 -m pip install -r requirements.txt

sudo -S cp ./signage.service /etc/systemd/system/signage.service
sudo -S systemctl --system daemon-reload
sudo -S systemctl enable signage
sudo -S systemctl start signage

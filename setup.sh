python3 -m pip install -r requirements.txt

sudo cp ./signage.service /etc/systemd/system/signage.service
sudo systemctl --system daemon-reload
sudo systemctl enable signage
sudo systemctl start signage

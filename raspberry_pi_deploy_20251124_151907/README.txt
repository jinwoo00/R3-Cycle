# R3-Cycle Raspberry Pi Deployment Package

## Quick Setup Instructions

### Option 1: USB Drive Transfer (Easiest)

1. **Copy this entire folder to USB drive**
   - Copy the aspberry_pi_deploy_* folder to a USB drive

2. **Transfer to Raspberry Pi:**
   - Insert USB drive into Raspberry Pi
   - Mount USB drive:
     `ash
     sudo mkdir -p /mnt/usb
     sudo mount /dev/sda1 /mnt/usb
     # Or use: lsblk to find your USB device
     `
   - Copy files:
     `ash
     sudo cp -r /mnt/usb/raspberry_pi_deploy_* /home/pi/r3cycle
     sudo chown -R pi:pi /home/pi/r3cycle
     `
   - Run setup:
     `ash
     cd /home/pi/r3cycle
     sudo bash setup.sh
     `

3. **Reboot:**
   `ash
   sudo reboot
   `

### Option 2: SCP Transfer (Requires SSH/Network)

From Windows PowerShell:
`powershell
scp -r raspberry_pi_deploy_* pi@<RASPBERRY_PI_IP>:/home/pi/r3cycle
`

Then SSH to Raspberry Pi:
`ash
ssh pi@<RASPBERRY_PI_IP>
cd /home/pi/r3cycle
sudo bash setup.sh
sudo reboot
`

### Option 3: Git Clone (If code is in Git repository)

On Raspberry Pi:
`ash
cd /home/pi
git clone <your-repo-url> r3cycle
cd r3cycle
sudo bash setup.sh
sudo reboot
`

## After Setup

1. **Edit configuration:**
   `ash
   nano config.py
   # Update: API_BASE_URL = "http://YOUR_BACKEND_IP:3000/api"
   `

2. **Run tests:**
   `ash
   # Test backend connection
   python3 tests/test_api.py
   
   # Test all hardware
   sudo python3 tests/run_all_tests.py
   `

3. **Start system:**
   `ash
   sudo python3 main.py
   `

## Files Included

- main.py - Main program
- config.py - Configuration file
- ealtime_client.py - Real-time WebSocket client
- 	ests/ - Hardware test scripts
- setup.sh - Automated setup script
- All other required files

Generated: 2025-11-24 15:19:07


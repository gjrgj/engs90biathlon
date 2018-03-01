# engs90biathlon
An app written for Engs 90 in partnership with the US Biathlon Team.

# PREREQUISITES
Have Python 3 installed on your computer. If you don't have it installed yet, you can get it by using Homebrew. Copy and paste the following command into Terminal and press enter:

`/usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"`

Once that's complete, run `brew install python3`. That's all for prereqs.

# SETUP
Open up an instance of Terminal and navigate to the directory you wish your project files to be located in. First clone the repo with `git clone https://github.com/gjrgj/engs90biathlon.git`. Next, run the following commands in order:

`make env`

`source venv/bin/activate`

`make run`

We make use of Python virtual environments to standardize expected behavior.

# OPERATION
First, turn on the Pi Zero attached to your rifle. Make sure it has been on for at least a minute or so before proceeding as it takes a bit of time to set up the onboard wifi and DHCP server. Next, run the command `make run` in Terminal and wait for a connection to be made between your computer and the rifle. If successful, everything should boot up and data should begin being collected. If you wish to run laser tracking, click *Start* on the control panel that comes up.

Note that sometimes the connection isn't made on the first try. If that happens, just run `make run` until it successfully connects. Data will be stored in folders within `stored_data` where folder names are timestamped based on when the application was booted up. Each folder will contain a `.csv` file with logged sensor data and a `.avi` file with logged laser tracking data.

# FAQ
## Why can I not access the internet during operation?
Because our connection method of choice is SSH through WiFi, your computer disconnects from the current network it's connected to and connects to the Pi Zero on the rifle. This Pi Zero is not connected to the larger Internet. Using Bluetooth would mediate this problem but we would lose a significant amount of the connection range/reliability.

## Does this work on Windows?
Not yet. However, the only segment of code that is OSX-specific is the automated wifi connecting - it uses the Airport script that is built in to all Macs and gives access to several different functions of the onboard wireless chip on the computer. Parallels exist for Windows and extending this software would not be too difficult. As all included Python libraries are cross-platform.

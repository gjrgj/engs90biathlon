# engs90biathlon
An app written for Engs 90 in partnership with the US Biathlon Team.

![GUI](/assets/gui.png)

# PREREQUISITES
First, open a Terminal window. If you don't have Python 3 installed on your computer, you can get it by using Homebrew. If you don't have Homebrew, install it first by running the following command in Terminal:

`/usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"`

Once that's complete, run `brew install python3`. That's all for prereqs.

# SETUP
Open up an instance of Terminal and navigate to the directory you wish your project files to be located in. First clone the repo with `git clone https://github.com/gjrgj/engs90biathlon.git`. Next type `cd engs90biathlon` to enter the project directory. Next, run `make all` and wait for everything to install. The application should start up automatically. In the future you can just type `make run` to boot it up. For more granularity in your installation check out the Makefile in the base directory.

Note: We make use of Python virtual environments to standardize expected behavior.

# OPERATION
First, turn on the Pi Zero attached to your rifle. Make sure it has been on for at least a minute or so before proceeding as it takes a bit of time to set up the onboard wifi and DHCP server. Next, run the command `make run` in Terminal and wait for a connection to be made between your computer and the rifle. If successful, everything should boot up and data should begin being collected. If you wish to run laser tracking, click *Start* on the control panel that comes up.

Note that sometimes the connection isn't made on the first try. If that happens, just run `make run` until it successfully connects. Data will be stored in folders within `stored_data` where folder names are timestamped based on when the data capture began. Each folder will contain a `.csv` file with logged sensor data and a `.avi` file with logged laser tracking data. These can be viewed in most common spreadsheet/video viewing software.

# FAQ
### Why can I not access the internet during operation?
Because our connection method of choice is SSH through WiFi, your computer disconnects from the current network it's connected to and connects to the Pi Zero on the rifle. This Pi Zero is not connected to the larger Internet. Using Bluetooth would mediate this problem but we would lose a significant amount of the connection range/reliability.

### Does this work on Windows?
Not yet. However, the only segment of code that is OSX-specific is the automated wifi connection handling - it uses the Airport script that is built into all Macs and gives access to several different functions of the onboard wireless chip on the computer. Parallels exist for Windows and extending this software would not be too difficult as all included Python libraries are cross-platform.

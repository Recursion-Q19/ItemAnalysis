To make an executable file, the best practice is to create a Python virtual environment (venv) and install the required packages for this project. Then, build and create the executable using the following command in the terminal. For example, if you run this on Windows machine, you will get an .exe file that can be executed on a Windows machine. 

```bash
pyinstaller --onefile --clean --noconsole --exclude-module tensorflow --exclude-module torch --exclude-module keras --exclude-module sklearn --exclude-module PyQt5 --exclude-module PySide6 --add-data "templates;templates" app.py
```

**Notes:**

* You need to install PyInstaller on your machine to be able to run this command.
* The ```bash --exclude-module ``` options are added because these package were present in my test environment. They ensure that none of those packages are included in the binary file as otherwise the binary file becomes large. If you are sure you do not have them installed, you can simply remove these exclude flags.

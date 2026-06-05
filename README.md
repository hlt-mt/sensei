# sensei
Sensei – Web GUI to edit subtitles


components:

- **Frontend** (Vue 3 + Vite)

---

## Functionalities

- Integrated editor to modify subtitle text and time stamps

---

## Tech Stack

Frontend:
- Vue 3
- Vite
- JavaScript
- npm

---


## Requirements

The system requires:
1. a working docker installation (tested with version 29.1.4)



## Download

The following files are to be downloaded:
1. the docker image sensei_gui v1.0 [image.sensei_gui__v1_0.tar.gz (0.2 GB)](https://fbk.sharepoint.com/:u:/s/MTUnit/IQA1xOuMyMXmRqm7xKrDtg9qAd4eJ80BBwp0FppRB2KYF1o?e=oWohus)
2. the software [sw.tar.gz (0.02 GB)](https://fbk.sharepoint.com/:u:/s/MTUnit/IQChqyMJutSVS53KUtR6EAjIAUFRtY2cTBEBTkb-7LtvOwQ?e=2xmQmP)



## Installation

### Add docker image
Add the dowloaded docker image to the docker environment with the following command:
```
docker load < image.sensei_gui__v1_0.tar.gz
```

### Add software
Create a directory (p.es. $HOME/sensei) and extract there the software:
```
mkdir -p $HOME/sensei
cd $HOME/sensei
tar xvfz sw.tar.gz
```


## Usage

In order to utilize the sensei system, you need to start it with the following command:

```
bash DO_sensei_start.sh
```

Then in your browser open the following URL:
```
localhost:5173
```

After using sensei, please end the system with following command:
```
bash DO_sensei_end.sh
```

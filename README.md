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
1. the docker image sensei_gui v1.0 [non-macOS: image.sensei_gui__v1_0.tar.gz (0.43 GB)](https://fbk.sharepoint.com/:u:/s/MTUnit/IQCd3H9b2OLXQKXW1JyIEfkaAdqv206YX8FLVJ0eJNdMRrE?e=e744SY) or [macOS: MAC.image.sensei_gui__v1_0.tar.gz (1.08 GB)](https://fbk.sharepoint.com/:u:/s/MTUnit/IQAUCqdx6EGUTJx0x6XGspbJAekRjHopqX2nxW-1EPkCUVo?e=ocaY8M)
2. the software [sw_ULTRALITE.tar.gz (0.02 GB)](https://fbk.sharepoint.com/:u:/s/MTUnit/IQAak5ah_cNnSa08lnKZSH89ATsH2n_r8oxY6jmUzxa1nh4?e=GCX2QZ)



## Installation

### Add docker image
Add the dowloaded docker image to the docker environment with the following command:
```
docker load < image.sensei_gui__v1_0.tar.gz
docker tag sensei_gui:v1.0 sensei_gui:latest
```

### Add software
Create a directory (p.es. $HOME/sensei) and extract there the software:
```
mkdir -p $HOME/sensei
cd $HOME/sensei
tar xvfz sw_ULTRALITE.tar.gz
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

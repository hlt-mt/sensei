# sensei
Sensei – Web GUI to manage AI Subtitle Generator &amp; Translator


Two are the components:

- **Frontend** (Vue 3 + Vite)
- **Backend** (FastAPI + SQLAlchemy)

---

## Functionalities

- ️Automatic generation of transcription subtitles (in the language spoken in the video)
- Automatic generation of translation subtitles, in a target language
- Integrated editor to modify subtitle text and time stamps

---

## Tech Stack

Frontend:
- Vue 3
- Vite
- JavaScript
- npm

Backend:
- FastAPI
- SQLAlchemy
- Pydantic Settings
- Uvicorn

---

## Requirements

The system requires:
1. a working docker installation (tested with version 29.1.4)


## Download

The following archives are to be downloaded:
1. the HuggingFace cache archive [cache_huggingface.tar.gz (11.5 GB)](https://fbk.sharepoint.com/:u:/s/MTUnit/IQCPmGMLVcCoR7yyfpCfrK-GAXFjaRjMU71Z_oNkCVrv0iA?e=l9Aeal)
2. the SHAS and WHISPER cache archive [cache_shas-whisper.tar.gz (3.2 GB)](https://fbk.sharepoint.com/:u:/s/MTUnit/IQBZc9bKSI-HQoHluxjdLcgOAdynPSb-dokQk6-hht9DHLQ?e=XvcQSs)
3. the software [sw_FULL.tar.gz (0.7 GB)](https://fbk.sharepoint.com/:u:/s/MTUnit/IQD_FU4kpPl7R52UPjliQRWEAaSEtOyxCtxSBXGedKxBlgI?e=voU8j0)

and the following docker images:
* non-macOS users:
   1. [image.shhe_v5-1.tar.gz (7.4 GB)](https://fbk.sharepoint.com/:u:/s/MTUnit/IQAJXMTrSn6ZS4vFlFQ-pwEmAc-dkH7O2Hr0R11CYVoRYhU?e=VUfeEj)
   2. [image.whma_v5-1.tar.gz (8.6 GB)](https://fbk.sharepoint.com/:u:/s/MTUnit/IQAcROjBLY0qTpCr7LSMDlRBAUaBE3ixpEwR9Ask0StkK4I?e=tU8GDP)
   3. [image.sensei_backend__v1_0.tar.gz (0.3 GB)](https://fbk.sharepoint.com/:u:/s/MTUnit/IQCpVnG6q0BnTaOOddg3P9A-AVOZ49G1KUoA_P2HBtHJJGc?e=jyxqdO)
   4. [image.sensei_gui__v1_0.tar.gz (0.43 GB)]((https://fbk.sharepoint.com/:u:/s/MTUnit/IQCd3H9b2OLXQKXW1JyIEfkaAdqv206YX8FLVJ0eJNdMRrE?e=e744SY)
* macOS users:
   1. [MAC.image.shhe_v5-1.tar.gz (5.4 GB)](https://fbk.sharepoint.com/:u:/s/MTUnit/IQDMrdmeeYelTbxsfNje8L7_AU237b-C9vW7RwuGjZWTx9U?e=8JI1qe)
   2. [MAC.image.whma_v5-1.tar.gz (10.3 GB)](https://fbk.sharepoint.com/:u:/s/MTUnit/IQBiPZdh4_0ZS5iGNKl14NIvAQz0sxUNtJZSy-6CSSB-iHU?e=9r2IlF)
   3. [MAC.image.sensei_backend__v1_0.tar.gz (0.8 GB)](https://fbk.sharepoint.com/:u:/s/MTUnit/IQDwFlL2wS7mTbN6ty9IHAchAeSUkqR7NTDzaMq57h1Zd2o?e=SsgCf9)
   4. [MAC.image.sensei_gui__v1_0.tar.gz (1.08 GB)](https://fbk.sharepoint.com/:u:/s/MTUnit/IQAUCqdx6EGUTJx0x6XGspbJAekRjHopqX2nxW-1EPkCUVo?e=ocaY8M)


## Installation

### Add docker images
Add the four dowloaded docker images to the docker environment with the following commands:
* non-macOS users:
```
docker load < image.shhe-v5_1.tar.gz
docker load < image.whma-v5_1.tar.gz
docker load < image.sensei_backend__v1_0.tar.gz
docker load < image.sensei_gui__v1_0.tar.gz
```
* macOS users:
```
docker load < MAC.image.shhe-v5_1.tar.gz
docker load < MAC.image.whma-v5_1.tar.gz
docker load < MAC.image.sensei_backend__v1_0.tar.gz
docker load < MAC.image.sensei_gui__v1_0.tar.gz
```

then add tag to the latest version for each image:

```
docker tag shhe:v5.1 shhe:latest
docker tag whma:v5.1 whma:latest
docker tag sensei_frontend:v1.0 sensei_frontend:latest
docker tag sensei_gui:v1.0 sensei_gui:latest


### Add cache models
```
cd $HOME/.cache
tar xvfz cache_huggingface.tar.gz
tar xvfz cache_shas-whisper.tar.gz
```

### Add software
Create a directory (p.es. $HOME/sensei) and extract there the software:
```
mkdir -p $HOME/sensei
cd $HOME/sensei
tar xvfz sw_FULL.tar.gz
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


## Application workflow

1. A video file is loaded
2. The system automatically generates the transcription subtitles
3. Transcription subtitles are automatically translated
4. Both transcription and translation subtitles can be modified by the user by means of the integrated editor
5. Both transcription and translation subtitles are exported as srt files 

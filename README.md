# NFT-scan: IPFS Upload & Storage Service

A minimal backend using FastAPI that allows uploading of images, files, or text and stores the content on IPFS. The service generates a unique NFT ID and returns the IPFS Content Identifier (CID) for both the content and its metadata.

## Features

- Upload any file to IPFS and receive a CID
- Generate NFT metadata and store it on IPFS
- Retrieve NFT metadata and content CID by NFT ID
- Dockerized setup with IPFS node included

## Getting Started

### Prerequisites

- Docker and Docker Compose

### Running the Service

1. Clone this repository
2. Start the services:

```bash
docker-compose up -d
```

This will start both the FastAPI backend and an IPFS node.

3. Access the API documentation at `http://localhost:7070/docs`

## API Endpoints

### Upload Content

**POST** `/upload/`

Upload content to IPFS and create NFT metadata.

**Form Parameters:**

- `file` (optional): The file to upload (image, document, etc.)
- `name` (required): Name of the NFT
- `description` (required): Description of the NFT
- `attributes` (optional): JSON string of attributes for the NFT

**Example Response:**

```json
{
  "nft_id": "550e8400-e29b-41d4-a716-446655440000",
  "content_cid": "QmW2WQi7j6c7UgJTarActp7tDNikE4B2qXtFCfLPdsgaTQ",
  "metadata_cid": "QmW2WQi7j6c7UgJTarActp7tDNikE4B2qXtFCfLPdsgaTQ",
  "metadata": {
    "name": "My NFT",
    "description": "This is my first NFT",
    "attributes": [],
    "image": "ipfs://QmW2WQi7j6c7UgJTarActp7tDNikE4B2qXtFCfLPdsgaTQ",
    "content_type": "image/jpeg"
  }
}
```

### Retrieve NFT

**GET** `/nft/{nft_id}`

Retrieve NFT metadata and content CID by NFT ID.

**Path Parameters:**

- `nft_id`: The unique identifier of the NFT

**Example Response:** Same as the upload response format

### Health Check

**GET** `/health`

Check the health of the service and IPFS connection.

**Example Response:**

```json
{
  "status": "ok",
  "ipfs": "connected"
}
```

## Architecture

The project consists of two main components:

1. **FastAPI Backend**: Handles HTTP requests, file processing, and IPFS interactions
2. **IPFS Node**: Stores and retrieves content on the IPFS network

## Data Storage

- Uploaded files are temporarily stored before being added to IPFS
- NFT metadata is stored locally in `/data/metadata/` and on IPFS
- IPFS data is persisted through Docker volumes

## License

MIT

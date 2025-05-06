import os
import json
import ipfshttpclient
import uvicorn
import shutil
import glob
import io
import qrcode
from typing import Dict, Optional, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel
from pathlib import Path
from uuid import uuid4

app = FastAPI(title="NFT IPFS Backend", description="A backend for NFT storage on IPFS")

# Configure IPFS client
IPFS_HOST = os.getenv("IPFS_HOST", "/dns/ipfs/tcp/5001/http")
metadata_dir = Path("./data/metadata")
uploads_dir = Path("./data/uploads")

# Create directories if they don't exist
metadata_dir.mkdir(parents=True, exist_ok=True)
uploads_dir.mkdir(parents=True, exist_ok=True)

# Connect to IPFS - configure with environment or default to local node
def get_ipfs_client():
    try:
        # Try connecting to the IPFS node
        return ipfshttpclient.connect(IPFS_HOST)
    except Exception as e:
        print(f"Error connecting to IPFS: {e}")
        return None

class NFTResponse(BaseModel):
    nft_id: str
    content_cid: str
    metadata_cid: str
    metadata: Dict

class NFTListResponse(BaseModel):
    nfts: List[NFTResponse]
    total_count: int

@app.post("/upload/", response_model=NFTResponse)
async def upload_to_ipfs(
    file: Optional[UploadFile] = File(None),
    name: str = Form(...),
    description: str = Form(...),
    attributes: Optional[str] = Form(None)
):
    """
    Upload content to IPFS and create NFT metadata
    """
    try:
        # Generate a unique NFT ID
        nft_id = str(uuid4())
        
        # Process attributes if provided
        nft_attributes = []
        if attributes:
            try:
                nft_attributes = json.loads(attributes)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid attributes JSON format")
        
        # Create metadata
        metadata = {
            "name": name,
            "description": description,
            "attributes": nft_attributes,
        }
        
        # Initialize IPFS client
        ipfs_client = get_ipfs_client()
        if not ipfs_client:
            raise HTTPException(status_code=503, detail="IPFS connection failed")
        
        # Handle file upload if provided
        content_cid = None
        if file:
            # Save the uploaded file temporarily
            file_path = uploads_dir / f"{nft_id}_{file.filename}"
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Upload file to IPFS
            ipfs_res = ipfs_client.add(file_path)
            content_cid = ipfs_res['Hash']
            
            # Update metadata with content info
            metadata["image"] = f"ipfs://{content_cid}"
            metadata["content_type"] = file.content_type
            
            # Clean up the temporary file
            os.remove(file_path)
        
        # Add metadata to IPFS
        metadata_json = json.dumps(metadata)
        metadata_file = metadata_dir / f"{nft_id}.json"
        with open(metadata_file, "w") as f:
            f.write(metadata_json)
        
        metadata_res = ipfs_client.add(metadata_file)
        metadata_cid = metadata_res['Hash']
        
        # Store the NFT data locally for later retrieval
        nft_data = {
            "nft_id": nft_id,
            "content_cid": content_cid,
            "metadata_cid": metadata_cid,
            "metadata": metadata
        }
        
        with open(metadata_dir / f"{nft_id}_data.json", "w") as f:
            json.dump(nft_data, f)
        
        return NFTResponse(**nft_data)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading to IPFS: {str(e)}")
    finally:
        if 'ipfs_client' in locals() and ipfs_client:
            ipfs_client.close()

@app.get("/nft/{nft_id}", response_model=NFTResponse)
async def get_nft(nft_id: str):
    """
    Retrieve NFT metadata and content CID by NFT ID
    """
    try:
        # Check if NFT exists
        nft_data_file = metadata_dir / f"{nft_id}_data.json"
        if not nft_data_file.exists():
            raise HTTPException(status_code=404, detail="NFT not found")
        
        # Load NFT data
        with open(nft_data_file, "r") as f:
            nft_data = json.load(f)
        
        return NFTResponse(**nft_data)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving NFT: {str(e)}")

@app.get("/nfts/", response_model=NFTListResponse)
async def list_all_nfts():
    """
    List all NFTs stored in the system
    """
    try:
        # Get all NFT data files
        nft_data_files = list(metadata_dir.glob("*_data.json"))
        
        nfts = []
        for nft_file in nft_data_files:
            try:
                with open(nft_file, "r") as f:
                    nft_data = json.load(f)
                    nfts.append(NFTResponse(**nft_data))
            except Exception as e:
                print(f"Error loading NFT data from {nft_file}: {e}")
                continue
        
        # Sort NFTs by name if available
        nfts.sort(key=lambda x: x.metadata.get("name", ""), reverse=True)
        
        return NFTListResponse(nfts=nfts, total_count=len(nfts))
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing NFTs: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    ipfs_status = "connected"
    try:
        client = get_ipfs_client()
        if client:
            client.close()
        else:
            ipfs_status = "disconnected"
    except:
        ipfs_status = "disconnected"
    
    return {"status": "ok", "ipfs": ipfs_status}

@app.get("/qrcode/{nft_id}")
async def generate_qr_code(nft_id: str):
    """
    Generate a QR code for the NFT content based on its CID
    """
    try:
        # Check if NFT exists
        nft_data_file = metadata_dir / f"{nft_id}_data.json"
        if not nft_data_file.exists():
            raise HTTPException(status_code=404, detail="NFT not found")
        
        # Load NFT data
        with open(nft_data_file, "r") as f:
            nft_data = json.load(f)
        
        # Get CID from NFT data
        content_cid = nft_data.get("content_cid")
        if not content_cid:
            content_cid = nft_data.get("metadata_cid")  # Fallback to metadata CID if no content
        
        # Generate a QR code for the IPFS URL
        ipfs_url = f"ipfs://{content_cid}"
        img = qrcode.make(ipfs_url)
        
        # Save the QR code to a bytes buffer
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)  # Reset buffer position
        
        # Return the image
        return StreamingResponse(img_bytes, media_type="image/png")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating QR code: {str(e)}")

@app.get("/qrcode/gateway/{nft_id}")
async def generate_gateway_qr_code(nft_id: str, gateway: str = "ipfs.io"):
    """
    Generate a QR code for the NFT content using a public gateway URL
    """
    try:
        # Check if NFT exists
        nft_data_file = metadata_dir / f"{nft_id}_data.json"
        if not nft_data_file.exists():
            raise HTTPException(status_code=404, detail="NFT not found")
        
        # Load NFT data
        with open(nft_data_file, "r") as f:
            nft_data = json.load(f)
        
        # Get CID from NFT data
        content_cid = nft_data.get("content_cid")
        if not content_cid:
            content_cid = nft_data.get("metadata_cid")  # Fallback to metadata CID if no content
        
        # Generate a QR code for the gateway URL
        gateway_url = f"https://{gateway}/ipfs/{content_cid}"
        img = qrcode.make(gateway_url)
        
        # Save the QR code to a bytes buffer
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)  # Reset buffer position
        
        # Return the image
        return StreamingResponse(img_bytes, media_type="image/png")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating QR code: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=7070, reload=True)
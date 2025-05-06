# app/backend/main.py
import io
import os
import uuid
import torch
import base64
from PIL import Image
import numpy as np
import torch.optim as optim
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from typing import Optional
from torchvision import transforms, models

# Create the FastAPI app
app = FastAPI(
    title="Neural Style Transfer API",
    description="API for Neural Style Transfer using VGG19",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create upload directory if it doesn't exist
os.makedirs("uploads", exist_ok=True)
os.makedirs("results", exist_ok=True)

# Load VGG19 model
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def load_vgg_model():
    vgg = models.vgg19(pretrained=True).features
    # Freeze all VGG parameters
    for param in vgg.parameters():
        param.requires_grad_(False)
    vgg.to(device)
    return vgg

vgg = load_vgg_model()

# Image processing functions
def load_image(img_path=None, img_data=None, max_size=512, shape=None):
    """Load an image from a file path or bytes data"""
    if img_path:
        image = Image.open(img_path).convert('RGB')
    else:
        image = Image.open(io.BytesIO(img_data)).convert('RGB')
    
    # Resize to maintain aspect ratio
    if max(image.size) > max_size:
        ratio = max_size / max(image.size)
        new_size = tuple([int(x * ratio) for x in image.size])
        image = image.resize(new_size, Image.LANCZOS)
    
    if shape is not None:
        image = image.resize(shape[-2:], Image.LANCZOS)
        
    # Transform the image
    in_transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.485, 0.456, 0.406), 
                             (0.229, 0.224, 0.225))
    ])
    
    # Add batch dimension
    image = in_transform(image)[:3,:,:].unsqueeze(0)
    
    return image

def im_convert(tensor):
    """Convert tensor to numpy image"""
    image = tensor.to("cpu").clone().detach()
    image = image.numpy().squeeze()
    image = image.transpose(1, 2, 0)
    image = image * np.array((0.229, 0.224, 0.225)) + np.array((0.485, 0.456, 0.406))
    image = image.clip(0, 1)
    return (image * 255).astype(np.uint8)

def get_features(image, model):
    """Extract features from image using VGG model"""
    layers = {'0': 'conv1_1',
              '5': 'conv2_1', 
              '10': 'conv3_1', 
              '19': 'conv4_1',
              '21': 'conv4_2',  # content representation
              '28': 'conv5_1'}
    
    features = {}
    x = image
    for name, layer in model._modules.items():
        x = layer(x)
        if name in layers:
            features[layers[name]] = x
            
    return features

def gram_matrix(tensor):
    """Calculate Gram Matrix"""
    _, d, h, w = tensor.size()
    tensor = tensor.view(d, h * w)
    gram = torch.mm(tensor, tensor.t())
    return gram

# Neural Style Transfer function
def perform_style_transfer(content_img, style_img, 
                          content_weight=1.0, style_weight=1e6,
                          steps=300, learning_rate=0.003,
                          style_weights=None):
    """Perform neural style transfer"""
    if style_weights is None:
        style_weights = {'conv1_1': 1.0,
                        'conv2_1': 0.8,
                        'conv3_1': 0.5,
                        'conv4_1': 0.3,
                        'conv5_1': 0.1}
    
    # Get features
    content_features = get_features(content_img, vgg)
    style_features = get_features(style_img, vgg)
    
    # Calculate gram matrices for style features
    style_grams = {layer: gram_matrix(style_features[layer]) for layer in style_features}
    
    # Initialize target image (start with content image)
    target = content_img.clone().requires_grad_(True).to(device)
    
    # Set up optimizer
    optimizer = optim.Adam([target], lr=learning_rate)
    
    # Track progress
    progress = []
    
    for step in range(1, steps + 1):
        # Get target features
        target_features = get_features(target, vgg)
        
        # Calculate content loss
        content_loss = torch.mean((target_features['conv4_2'] - content_features['conv4_2'])**2)
        
        # Calculate style loss
        style_loss = 0
        for layer in style_weights:
            target_feature = target_features[layer]
            target_gram = gram_matrix(target_feature)
            _, d, h, w = target_feature.shape
            style_gram = style_grams[layer]
            layer_style_loss = style_weights[layer] * torch.mean((target_gram - style_gram)**2)
            style_loss += layer_style_loss / (d * h * w)
        
        # Calculate total loss
        total_loss = content_weight * content_loss + style_weight * style_loss
        
        # Update target image
        optimizer.zero_grad()
        total_loss.backward()
        optimizer.step()
        
        # Track progress at intervals
        if step % (steps // 10) == 0 or step == steps:
            progress_info = {
                "step": step,
                "total_loss": total_loss.item(),
                "content_loss": content_loss.item(),
                "style_loss": style_loss.item()
            }
            progress.append(progress_info)
    
    # Convert final target image to PIL Image
    final_img = im_convert(target)
    return final_img, progress

# API models
class StyleTransferRequest(BaseModel):
    content_weight: float = 1.0
    style_weight: float = 1e6
    steps: int = 300
    learning_rate: float = 0.003
    conv1_1_weight: float = 1.0
    conv2_1_weight: float = 0.8
    conv3_1_weight: float = 0.5
    conv4_1_weight: float = 0.3
    conv5_1_weight: float = 0.1

# API routes
@app.post("/upload/")
async def upload_images(content_image: UploadFile = File(...), 
                        style_image: UploadFile = File(...)):
    """Upload content and style images"""
    try:
        # Generate unique IDs for the images
        content_id = str(uuid.uuid4())
        style_id = str(uuid.uuid4())
        
        # Save content image
        content_path = f"uploads/{content_id}.jpg"
        with open(content_path, "wb") as f:
            f.write(await content_image.read())
            
        # Save style image
        style_path = f"uploads/{style_id}.jpg"
        with open(style_path, "wb") as f:
            f.write(await style_image.read())
            
        return JSONResponse({
            "content_id": content_id,
            "style_id": style_id,
            "message": "Images uploaded successfully"
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/transfer/")
async def transfer_style(
    content_id: str = Form(...),
    style_id: str = Form(...),
    content_weight: float = Form(1.0),
    style_weight: float = Form(1e6),
    steps: int = Form(300),
    learning_rate: float = Form(0.003),
    conv1_1_weight: float = Form(1.0),
    conv2_1_weight: float = Form(0.8),
    conv3_1_weight: float = Form(0.5),
    conv4_1_weight: float = Form(0.3),
    conv5_1_weight: float = Form(0.1)
):
    """Perform neural style transfer with the uploaded images"""
    try:
        # Load images
        content_path = f"uploads/{content_id}.jpg"
        style_path = f"uploads/{style_id}.jpg"
        
        if not os.path.exists(content_path) or not os.path.exists(style_path):
            raise HTTPException(status_code=404, detail="Images not found")
        
        # Validate parameters
        if steps < 50 or steps > 100000:
            raise HTTPException(status_code=400, detail="Steps should be between 50 and 1000")
        
        # Load images for processing
        content_img = load_image(img_path=content_path).to(device)
        style_img = load_image(img_path=style_path, shape=content_img.shape[-2:]).to(device)
        
        # Set style weights
        style_weights = {
            'conv1_1': conv1_1_weight,
            'conv2_1': conv2_1_weight,
            'conv3_1': conv3_1_weight,
            'conv4_1': conv4_1_weight,
            'conv5_1': conv5_1_weight
        }
        
        # Perform style transfer
        final_img, progress = perform_style_transfer(
            content_img, style_img,
            content_weight=content_weight,
            style_weight=style_weight,
            steps=steps,
            learning_rate=learning_rate,
            style_weights=style_weights
        )
        
        # Save the result
        result_id = str(uuid.uuid4())
        result_path = f"results/{result_id}.jpg"
        Image.fromarray(final_img).save(result_path)
        
        # Convert image to base64 for preview
        buffered = io.BytesIO()
        Image.fromarray(final_img).save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        return JSONResponse({
            "result_id": result_id,
            "preview": f"data:image/jpeg;base64,{img_str}",
            "progress": progress
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download/{result_id}")
async def download_result(result_id: str):
    """Download the result image"""
    result_path = f"results/{result_id}.jpg"
    if not os.path.exists(result_path):
        raise HTTPException(status_code=404, detail="Result not found")
    
    # Return the file as a download response
    return FileResponse(
        path=result_path,
        filename=f"neural_style_transfer_{result_id}.jpg",
        media_type="image/jpeg"
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    """Check if the API is running"""
    return {"status": "healthy", "device": str(device)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
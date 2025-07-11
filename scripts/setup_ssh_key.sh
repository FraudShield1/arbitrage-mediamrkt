#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}SSH Key Setup Script${NC}"
echo "=============================="

# Check for existing SSH keys
echo -e "\n${YELLOW}Checking for existing SSH keys...${NC}"
if [ -f ~/.ssh/id_ed25519.pub ] || [ -f ~/.ssh/id_rsa.pub ]; then
    echo -e "${GREEN}Found existing SSH key(s):${NC}"
    ls -la ~/.ssh/id_*.pub 2>/dev/null
    
    echo -e "\n${YELLOW}Your public key(s):${NC}"
    if [ -f ~/.ssh/id_ed25519.pub ]; then
        echo -e "\n${GREEN}Ed25519 key:${NC}"
        cat ~/.ssh/id_ed25519.pub
    fi
    if [ -f ~/.ssh/id_rsa.pub ]; then
        echo -e "\n${GREEN}RSA key:${NC}"
        cat ~/.ssh/id_rsa.pub
    fi
else
    echo -e "${YELLOW}No existing SSH keys found. Generating new Ed25519 key...${NC}"
    
    # Get email
    echo -e "\n${GREEN}Enter your email address:${NC}"
    read email
    
    # Generate new SSH key
    ssh-keygen -t ed25519 -C "$email"
    
    if [ $? -eq 0 ]; then
        echo -e "\n${GREEN}SSH key generated successfully!${NC}"
        echo -e "\n${YELLOW}Your public key:${NC}"
        cat ~/.ssh/id_ed25519.pub
    else
        echo -e "\n${RED}Error generating SSH key!${NC}"
        exit 1
    fi
fi

# Instructions for DigitalOcean
echo -e "\n${GREEN}Next steps:${NC}"
echo "1. Copy your public key (shown above)"
echo "2. Log into your DigitalOcean account"
echo "3. Go to Settings > Security > SSH Keys"
echo "4. Click 'Add SSH Key'"
echo "5. Paste your public key and give it a name"
echo -e "\n${YELLOW}After creating your droplet, test the connection with:${NC}"
echo "ssh -T root@your_droplet_ip" 
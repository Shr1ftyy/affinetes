#!/bin/bash
# Affinetes Quickstart CLI Demo
# This script demonstrates the complete workflow: init -> build -> run -> call -> push

set -e  # Exit on error

echo "========================================================================"
echo "  AFFINETES CLI QUICKSTART DEMO"
echo "  From Environment Creation to Docker Hub Publishing"
echo "========================================================================"
echo ""
echo "This demo shows the complete workflow:"
echo "  1. Initialize a new environment"
echo "  2. Build the Docker image"
echo "  3. Run the environment"
echo "  4. Call methods via CLI"
echo "  5. Publish to Docker Hub"
echo ""
echo "========================================================================"
echo ""

# Configuration
DOCKER_USERNAME="${DOCKER_USERNAME:-yourusername}"
ENV_NAME="my-calculator"
IMAGE_TAG="$ENV_NAME:v1.0"
CONTAINER_NAME="$ENV_NAME-demo"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Initialize Environment
echo -e "${BLUE}Step 1: Initialize New Environment${NC}"
echo "----------------------------------------------------------------------"
echo "Command: afs init $ENV_NAME --template actor"
echo ""

# Clean up any existing directory
rm -rf "$ENV_NAME"

afs init "$ENV_NAME" --template actor

echo -e "${GREEN}✓ Environment initialized in ./$ENV_NAME/${NC}"
echo ""

# Step 2: Customize the Environment
echo -e "${BLUE}Step 2: Customize Environment Code${NC}"
echo "----------------------------------------------------------------------"
echo "Adding calculator methods to env.py..."
echo ""

# Create custom calculator env.py
cat > "$ENV_NAME/env.py" << 'EOF'
"""Simple Calculator Environment"""

import os


class Actor:
    """Calculator Actor - performs basic math operations"""
    
    def __init__(self):
        """Initialize calculator with optional precision setting"""
        self.precision = int(os.getenv("PRECISION", "2"))
        self.name = "Calculator Environment"
    
    async def add(self, a: float, b: float) -> dict:
        """Add two numbers"""
        result = round(a + b, self.precision)
        return {
            "operation": "add",
            "inputs": {"a": a, "b": b},
            "result": result,
            "success": True
        }
    
    async def subtract(self, a: float, b: float) -> dict:
        """Subtract two numbers"""
        result = round(a - b, self.precision)
        return {
            "operation": "subtract",
            "inputs": {"a": a, "b": b},
            "result": result,
            "success": True
        }
    
    async def multiply(self, a: float, b: float) -> dict:
        """Multiply two numbers"""
        result = round(a * b, self.precision)
        return {
            "operation": "multiply",
            "inputs": {"a": a, "b": b},
            "result": result,
            "success": True
        }
    
    async def divide(self, a: float, b: float) -> dict:
        """Divide two numbers"""
        if b == 0:
            return {
                "operation": "divide",
                "inputs": {"a": a, "b": b},
                "result": None,
                "success": False,
                "error": "Division by zero"
            }
        
        result = round(a / b, self.precision)
        return {
            "operation": "divide",
            "inputs": {"a": a, "b": b},
            "result": result,
            "success": True
        }
    
    async def power(self, base: float, exponent: float) -> dict:
        """Raise a number to a power"""
        result = round(base ** exponent, self.precision)
        return {
            "operation": "power",
            "inputs": {"base": base, "exponent": exponent},
            "result": result,
            "success": True
        }
EOF

echo -e "${GREEN}✓ Custom calculator code added${NC}"
echo ""

# Step 3: Build Docker Image
echo -e "${BLUE}Step 3: Build Docker Image${NC}"
echo "----------------------------------------------------------------------"
echo "Command: afs build $ENV_NAME --tag $IMAGE_TAG"
echo ""

afs build "$ENV_NAME" --tag "$IMAGE_TAG"

echo -e "${GREEN}✓ Image built successfully: $IMAGE_TAG${NC}"
echo ""

# Step 4: Run Environment
echo -e "${BLUE}Step 4: Start Environment Container${NC}"
echo "----------------------------------------------------------------------"
echo "Command: afs run $IMAGE_TAG --name $CONTAINER_NAME --env PRECISION=3"
echo ""

# Clean up any existing container
docker stop "$CONTAINER_NAME" 2>/dev/null || true
docker rm "$CONTAINER_NAME" 2>/dev/null || true

afs run "$IMAGE_TAG" --name "$CONTAINER_NAME" --env PRECISION=3

echo -e "${GREEN}✓ Environment started: $CONTAINER_NAME${NC}"
echo ""
sleep 2  # Give container time to fully start

# Step 5: Call Methods
echo -e "${BLUE}Step 5: Call Calculator Methods${NC}"
echo "----------------------------------------------------------------------"
echo ""

echo -e "${YELLOW}Test 1: Addition (10 + 5)${NC}"
echo "Command: afs call $CONTAINER_NAME add --arg a=10 --arg b=5"
afs call "$CONTAINER_NAME" add --arg a=10 --arg b=5
echo ""

echo -e "${YELLOW}Test 2: Multiplication (7 * 6)${NC}"
echo "Command: afs call $CONTAINER_NAME multiply --arg a=7 --arg b=6"
afs call "$CONTAINER_NAME" multiply --arg a=7 --arg b=6
echo ""

echo -e "${YELLOW}Test 3: Division with Precision (100 / 3)${NC}"
echo "Command: afs call $CONTAINER_NAME divide --arg a=100 --arg b=3"
afs call "$CONTAINER_NAME" divide --arg a=100 --arg b=3
echo ""

echo -e "${YELLOW}Test 4: Power Calculation (2^10)${NC}"
echo "Command: afs call $CONTAINER_NAME power --arg base=2 --arg exponent=10"
afs call "$CONTAINER_NAME" power --arg base=2 --arg exponent=10
echo ""

echo -e "${YELLOW}Test 5: Error Handling (10 / 0)${NC}"
echo "Command: afs call $CONTAINER_NAME divide --arg a=10 --arg b=0"
afs call "$CONTAINER_NAME" divide --arg a=10 --arg b=0 || echo -e "${RED}Expected error caught${NC}"
echo ""

# Step 6: Docker Hub Publishing Instructions
echo -e "${BLUE}Step 6: Publishing to Docker Hub${NC}"
echo "----------------------------------------------------------------------"
echo ""
echo "To publish this environment to Docker Hub, follow these steps:"
echo ""
echo "1. Login to Docker Hub:"
echo -e "   ${YELLOW}docker login${NC}"
echo ""
echo "2. Tag the image with your Docker Hub username:"
echo -e "   ${YELLOW}docker tag $IMAGE_TAG docker.io/$DOCKER_USERNAME/$IMAGE_TAG${NC}"
echo -e "   ${YELLOW}docker tag $IMAGE_TAG docker.io/$DOCKER_USERNAME/$ENV_NAME:latest${NC}"
echo ""
echo "3. Push to Docker Hub:"
echo -e "   ${YELLOW}docker push docker.io/$DOCKER_USERNAME/$IMAGE_TAG${NC}"
echo -e "   ${YELLOW}docker push docker.io/$DOCKER_USERNAME/$ENV_NAME:latest${NC}"
echo ""
echo "4. Your environment is now public! Anyone can use it:"
echo -e "   ${YELLOW}afs run docker.io/$DOCKER_USERNAME/$ENV_NAME:latest --name calc --pull${NC}"
echo ""

# Alternative: Use affinetes build with --push
echo "Alternatively, rebuild and push in one command:"
echo -e "   ${YELLOW}afs build $ENV_NAME --tag $IMAGE_TAG --push --registry docker.io/$DOCKER_USERNAME${NC}"
echo ""

# Optional: Auto-publish if DOCKER_USERNAME is set and not default
if [ "$DOCKER_USERNAME" != "yourusername" ] && [ -n "$DOCKER_PUSH" ]; then
    echo -e "${YELLOW}Auto-publishing enabled (DOCKER_PUSH=1)...${NC}"
    echo ""
    
    docker tag "$IMAGE_TAG" "docker.io/$DOCKER_USERNAME/$IMAGE_TAG"
    docker tag "$IMAGE_TAG" "docker.io/$DOCKER_USERNAME/$ENV_NAME:latest"
    
    docker push "docker.io/$DOCKER_USERNAME/$IMAGE_TAG"
    docker push "docker.io/$DOCKER_USERNAME/$ENV_NAME:latest"
    
    echo -e "${GREEN}✓ Published to docker.io/$DOCKER_USERNAME/$ENV_NAME${NC}"
    echo ""
fi

# Cleanup
echo -e "${BLUE}Step 7: Cleanup${NC}"
echo "----------------------------------------------------------------------"
echo "Stopping and removing container..."
docker stop "$CONTAINER_NAME"
docker rm "$CONTAINER_NAME"
echo -e "${GREEN}✓ Container cleaned up${NC}"
echo ""
echo "Environment directory kept at: ./$ENV_NAME/"
echo "To remove it: rm -rf $ENV_NAME"
echo ""

# Summary
echo "========================================================================"
echo "  DEMO COMPLETE"
echo "========================================================================"
echo ""
echo "What we demonstrated:"
echo "  ✓ Created new environment with: afs init"
echo "  ✓ Customized calculator logic in env.py"
echo "  ✓ Built Docker image with: afs build"
echo "  ✓ Started container with: afs run"
echo "  ✓ Called methods with: afs call"
echo "  ✓ Showed Docker Hub publishing workflow"
echo ""
echo "Key Files Created:"
echo "  - $ENV_NAME/env.py      - Environment implementation"
echo "  - $ENV_NAME/Dockerfile  - Container configuration"
echo ""
echo "Next Steps:"
echo "  1. Explore the generated files in ./$ENV_NAME/"
echo "  2. Modify env.py to add your own methods"
echo "  3. Rebuild and test: afs build $ENV_NAME --tag $ENV_NAME:v2"
echo "  4. Publish to Docker Hub (see Step 6 above)"
echo ""
echo "To publish automatically, run:"
echo "  export DOCKER_USERNAME=your_dockerhub_username"
echo "  export DOCKER_PUSH=1"
echo "  ./quickstart_cli_demo.sh"
echo ""
echo "========================================================================"
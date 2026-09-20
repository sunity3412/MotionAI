#!/bin/bash
# Serving pod for the repeatability run. Ada only (ORT 1.22 is a CUDA 12 build;
# Blackwell risks the CUDA EP not loading). Network volume a5z753defc is required
# and pins the datacenter.
set -u
KEY=$(aws ssm get-parameter --name /sunity/motion/runpod-api-key --with-decryption \
      --profile sunity-motion --region ap-northeast-2 --query 'Parameter.Value' --output text)
GPUS=("NVIDIA L4" "NVIDIA GeForce RTX 4090" "NVIDIA RTX 4000 Ada Generation" "NVIDIA RTX 2000 Ada Generation" "NVIDIA L40S" "NVIDIA RTX A5000")
for GPU in "${GPUS[@]}"; do
  echo "trying: $GPU" >&2
  R=$(curl -s -m 40 -X POST https://api.runpod.io/graphql \
    -H "Content-Type: application/json" -H "Authorization: Bearer $KEY" \
    -d "{\"query\":\"mutation { podFindAndDeployOnDemand(input: { cloudType: SECURE, gpuCount: 1, gpuTypeId: \\\"$GPU\\\", name: \\\"sunity-serve-repeatability\\\", imageName: \\\"runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04\\\", networkVolumeId: \\\"a5z753defc\\\", volumeMountPath: \\\"/workspace\\\", containerDiskInGb: 50, ports: \\\"22/tcp,8000/http\\\", startSsh: true }) { id costPerHr machineId } }\"}")
  POD=$(echo "$R" | python3 -c "import json,sys;d=json.load(sys.stdin);p=(d.get('data') or {}).get('podFindAndDeployOnDemand');print(p['id'] if p else '')" 2>/dev/null)
  if [ -n "$POD" ]; then
    echo "$R"
    echo "CREATED $POD ($GPU)" >&2
    exit 0
  fi
  echo "  no stock / error: $(echo "$R" | head -c 200)" >&2
done
echo "ALL GPUS UNAVAILABLE" >&2
exit 1

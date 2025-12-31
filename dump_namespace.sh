#!/bin/bash

set -e

NAMESPACE="$1"

if [ -z "$NAMESPACE" ]; then
  echo "Usage: $0 <namespace>"
  exit 1
fi

kubectl get namespace "$NAMESPACE" >/dev/null 2>&1 || {
  echo "Namespace '$NAMESPACE' does not exist"
  exit 1
}

# Check if kubectl krew is installed
if ! kubectl krew version >/dev/null 2>&1; then
  echo "kubectl krew not found, installing..."
  
  # Install prerequisites
  sudo apt update
  sudo apt install -y git curl
  
  # Install krew
  (
    set -x
    cd "$(mktemp -d)" || exit 1
    OS="$(uname | tr '[:upper:]' '[:lower:]')"
    ARCH="$(uname -m | sed -e 's/x86_64/amd64/' -e 's/arm.*/arm/;s/aarch64/arm64/')"
    KREW="krew-${OS}_${ARCH}"
    curl -fsSLO "https://github.com/kubernetes-sigs/krew/releases/latest/download/${KREW}.tar.gz"
    tar zxvf "${KREW}.tar.gz"
    ./"${KREW}" install krew
  )

  export PATH="${KREW_ROOT:-$HOME/.krew}/bin:$PATH"
fi

# Check if kubectl-neat is installed
if ! kubectl neat --help >/dev/null 2>&1; then
  echo "kubectl-neat not found, installing..."
  kubectl krew install neat
fi

# Namespaced resources
RESOURCES_NS=(
  deployments.apps
  services
  configmaps
  secrets
  ingresses.networking.k8s.io
  persistentvolumeclaims
)

# Cluster-scoped resources
RESOURCES_CLUSTER=(
  persistentvolumes
)

echo "Exporting resources from namespace: $NAMESPACE"

mkdir -p namespaces/"$NAMESPACE"

# Dump namespaced resources
for r in "${RESOURCES_NS[@]}"; do
  names=$(kubectl get "$r" -n "$NAMESPACE" -o name 2>/dev/null || true)
  [ -z "$names" ] && continue

  echo "Dumping $r"

  for name in $names; do
    mkdir -p "$(dirname namespaces/$NAMESPACE/$name)"
    kubectl get "$name" -n "$NAMESPACE" -o yaml | kubectl neat > namespaces/$NAMESPACE/$name.yaml
    echo "Saved: namespaces/$NAMESPACE/$name.yaml"
  done
done

# Dump PVs (cluster-scoped)
for r in "${RESOURCES_CLUSTER[@]}"; do
  names=$(kubectl get "$r" -o name 2>/dev/null || true)
  [ -z "$names" ] && continue

  echo "Dumping $r"

  for name in $names; do
    mkdir -p "$(dirname namespaces/$NAMESPACE/$name)"
    kubectl get "$name" -o yaml | kubectl neat > namespaces/$NAMESPACE/$name.yaml
    echo "Saved: namespaces/$NAMESPACE/$name.yaml"
  done
done

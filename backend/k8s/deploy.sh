#!/bin/bash
# Customer Success Digital FTE - Kubernetes Deployment Script
# Automates common K8s deployment tasks

set -e

NAMESPACE="customer-success-fte"
REGISTRY="${REGISTRY:-docker.io}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed"
        exit 1
    fi
    
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    log_info "Prerequisites check passed"
}

# Create namespace
create_namespace() {
    log_info "Creating namespace: $NAMESPACE"
    kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
}

# Build and push images
build_images() {
    log_info "Building Docker images..."
    
    docker build -t ${REGISTRY}/customer-success-fte-api:${IMAGE_TAG} .
    docker build -f Dockerfile.worker -t ${REGISTRY}/customer-success-fte-worker:${IMAGE_TAG} .
    
    log_info "Images built successfully"
}

push_images() {
    log_info "Pushing Docker images to ${REGISTRY}..."
    
    docker push ${REGISTRY}/customer-success-fte-api:${IMAGE_TAG}
    docker push ${REGISTRY}/customer-success-fte-worker:${IMAGE_TAG}
    
    log_info "Images pushed successfully"
}

# Deploy stateful services (PostgreSQL, Kafka)
deploy_stateful() {
    log_info "Deploying stateful services..."
    
    kubectl apply -f k8s/statefulset.yaml -n $NAMESPACE
    
    log_info "Waiting for PostgreSQL to be ready..."
    kubectl wait --for=condition=ready pod -l app=postgres -n $NAMESPACE --timeout=300s
    
    log_info "Waiting for Kafka to be ready..."
    kubectl wait --for=condition=ready pod -l app=kafka -n $NAMESPACE --timeout=300s
    
    log_info "Stateful services deployed"
}

# Deploy application
deploy_app() {
    log_info "Deploying application..."
    
    # Update image references in deployment.yaml
    sed -i.bak "s|customer-success-fte-api:latest|${REGISTRY}/customer-success-fte-api:${IMAGE_TAG}|g" k8s/deployment.yaml
    sed -i.bak "s|customer-success-fte-worker:latest|${REGISTRY}/customer-success-fte-worker:${IMAGE_TAG}|g" k8s/deployment.yaml
    
    kubectl apply -f k8s/deployment.yaml -n $NAMESPACE
    
    # Restore original file
    mv k8s/deployment.yaml.bak k8s/deployment.yaml 2>/dev/null || true
    
    log_info "Application deployed"
}

# Deploy monitoring
deploy_monitoring() {
    log_info "Deploying monitoring stack..."
    
    kubectl apply -f k8s/monitoring.yaml -n $NAMESPACE
    
    log_info "Monitoring deployed"
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."
    
    echo ""
    log_info "Pods:"
    kubectl get pods -n $NAMESPACE
    
    echo ""
    log_info "Services:"
    kubectl get svc -n $NAMESPACE
    
    echo ""
    log_info "Deployments:"
    kubectl get deployments -n $NAMESPACE
    
    echo ""
    log_info "StatefulSets:"
    kubectl get statefulsets -n $NAMESPACE
    
    echo ""
    log_info "HPA:"
    kubectl get hpa -n $NAMESPACE
    
    # Wait for API to be ready
    log_info "Waiting for API to be ready..."
    kubectl wait --for=condition=ready pod -l app=api -n $NAMESPACE --timeout=120s
    
    log_info "Deployment verification complete"
}

# Full deployment
deploy_all() {
    check_prerequisites
    create_namespace
    build_images
    push_images
    deploy_stateful
    deploy_app
    deploy_monitoring
    verify_deployment
    
    log_info "=========================================="
    log_info "Deployment completed successfully!"
    log_info "=========================================="
}

# Rollback deployment
rollback() {
    log_info "Rolling back deployment..."
    
    kubectl rollout undo deployment/api-deployment -n $NAMESPACE
    kubectl rollout undo deployment/worker-deployment -n $NAMESPACE
    
    log_info "Rollback complete"
}

# Scale deployment
scale() {
    local component=$1
    local replicas=$2
    
    if [ -z "$component" ] || [ -z "$replicas" ]; then
        log_error "Usage: $0 scale <api|worker> <replicas>"
        exit 1
    fi
    
    log_info "Scaling $component to $replicas replicas..."
    kubectl scale deployment/${component}-deployment --replicas=$replicas -n $NAMESPACE
    
    log_info "Scale complete"
}

# View logs
logs() {
    local component=$1
    
    if [ -z "$component" ]; then
        log_error "Usage: $0 logs <api|worker|scheduler>"
        exit 1
    fi
    
    kubectl logs -f deployment/${component}-deployment -n $NAMESPACE
}

# Cleanup
cleanup() {
    log_warn "This will delete all resources in the $NAMESPACE namespace!"
    read -p "Are you sure? (y/N) " confirm
    
    if [ "$confirm" != "y" ]; then
        log_info "Cleanup cancelled"
        exit 0
    fi
    
    log_info "Deleting namespace..."
    kubectl delete namespace $NAMESPACE
    
    log_info "Cleanup complete"
}

# Show help
show_help() {
    echo "Customer Success Digital FTE - Kubernetes Deployment Script"
    echo ""
    echo "Usage: $0 <command>"
    echo ""
    echo "Commands:"
    echo "  deploy      Full deployment (build, push, deploy)"
    echo "  stateful    Deploy stateful services only (PostgreSQL, Kafka)"
    echo "  app         Deploy application only"
    echo "  monitoring  Deploy monitoring stack"
    echo "  verify      Verify deployment status"
    echo "  rollback    Rollback to previous deployment"
    echo "  scale       Scale deployment (usage: scale <api|worker> <replicas>)"
    echo "  logs        View logs (usage: logs <api|worker|scheduler>)"
    echo "  cleanup     Delete all resources"
    echo "  help        Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  REGISTRY    Docker registry (default: docker.io)"
    echo "  IMAGE_TAG   Image tag (default: latest)"
}

# Main
case "${1:-help}" in
    deploy)
        deploy_all
        ;;
    stateful)
        check_prerequisites
        create_namespace
        deploy_stateful
        ;;
    app)
        check_prerequisites
        create_namespace
        build_images
        push_images
        deploy_app
        verify_deployment
        ;;
    monitoring)
        deploy_monitoring
        ;;
    verify)
        verify_deployment
        ;;
    rollback)
        rollback
        ;;
    scale)
        scale "$2" "$3"
        ;;
    logs)
        logs "$2"
        ;;
    cleanup)
        cleanup
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        log_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac

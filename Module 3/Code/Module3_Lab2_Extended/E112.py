import copy

def simulate_federated_training(num_clients=3, epochs=1):
    global_model = SimpleMLP()
    client_models = [copy.deepcopy(global_model) for _ in range(num_clients)]

    # Simulate each client training
    for cid, client_model in enumerate(client_models):
        data, _ = get_dataset(remove_idx=cid * 10)
        data_loader = torch.utils.data.DataLoader(data, batch_size=64, shuffle=True)
        train_model(client_model, data_loader, epochs=epochs)

    # Aggregate (simple average)
    with torch.no_grad():
        for param in global_model.parameters():
            param.data = sum([client_param.data for client_param in [m for m in client_models]
                             for client_param in client_param.parameters()]) / num_clients

    return global_model, client_models

def remove_client_contribution(global_model, client_models, forget_id):
    # Simulate unlearning by averaging without client `forget_id`
    kept_clients = [m for i, m in enumerate(client_models) if i != forget_id]
    with torch.no_grad():
        for param in global_model.parameters():
            param.data = sum([client_param.data for client_param in kept_clients
                             for client_param in client_param.parameters()]) / len(kept_clients)

# Example
global_model, client_models = simulate_federated_training()
remove_client_contribution(global_model, client_models, forget_id=1)

import bittensor as bt

if __name__ == '__main__':
    threshold = int(input("Enter the threshold: "))
    subtensor = bt.Subtensor(network="finney")
    subnet_infos = subtensor.all_subnets()
    prev_tao_in = [subnet_info.tao_in for subnet_info in subnet_infos]
    while True:
        try:
            now_subnet_infos = subtensor.all_subnets()
            now_tao_in = [subnet_info.tao_in for subnet_info in now_subnet_infos]
            tao_flow = [float(now_tao_in[i] - prev_tao_in[i]) for i in range(len(now_tao_in))]
            for i in range(len(tao_flow)):
                if abs(tao_flow[i]) >= threshold:
                    print(f"SN {i:2d} => {round(float(now_subnet_infos[i].price), 5):>8.5f}, {round(tao_flow[i], 2):>8.2f}")

            print("***")
            prev_tao_in = now_tao_in
            subtensor.wait_for_block()
        except Exception as e:
            print(f"Error in watching_price: {e}")
            continue

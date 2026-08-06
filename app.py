from agents.supervisor import Supervisor


def main():

    supervisor = Supervisor()

    while True:

        query = input("\nAsk: ")

        if query.lower() == "exit":
            break

        agent = supervisor.process(query)

        print(f"\nSelected Agent: {agent}")


if __name__ == "__main__":
    main()
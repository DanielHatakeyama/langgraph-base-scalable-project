# TOdo do all auth automaticaslly ? or lazily?
from graph.main_graph import build_workflow

# main.py

def main():
    workflow = build_workflow()
    initial_state = {
        "topic": "Make an meeting called epic capstone meeting today at 11 PM Mountain time",
        "prompt": "Make an meeting called epic capstone meeting today at 11 PM Mountain times"
    }
    final_state = workflow.invoke(initial_state)
    print("Final state:", final_state)

if __name__ == "__main__":
    main()
     

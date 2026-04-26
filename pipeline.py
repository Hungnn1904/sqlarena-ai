from prefect import flow, task

@task
def planner():
    print("planning...")
    return "blueprint"

@task
def generator(bp):
    print("generating...")
    return "question"

@task
def verify(q):
    print("verifying...")
    return True

@flow
def generate_pipeline():
    bp = planner()
    q = generator(bp)
    verify(q)

if __name__ == "__main__":
    generate_pipeline()
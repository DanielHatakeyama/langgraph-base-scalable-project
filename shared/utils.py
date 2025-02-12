import os
import logging
from IPython.display import Image

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Draw Graph Utility
def draw_graph(graph, file_path):
    """
    Save the diagram of a compiled graph object to a specified file path.

    Parameters:
    - graph: The compiled graph object that has a method `get_graph()` which returns an object
             with a method `draw_mermaid_png()` to generate the diagram image.
    - file_path: The path where the diagram image will be saved.

    Example usage:
    draw_graph(graph, "diagrams/file.png")
    """
    try:
        # Generate the image from the graph
        img = Image(graph.get_graph().draw_mermaid_png())

        # Extract the directory from the file path
        directory = os.path.dirname(file_path)

        # Check if the directory exists, if not, create it
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
            logger.info(f"Created directory: {directory}")

        # Save the image to the specified file path
        with open(file_path, "wb") as png:
            png.write(img.data)

        logger.info(f"Diagram saved successfully to {file_path}")

    except Exception as e:
        logger.error(f"An error occurred while saving the diagram: {e}")

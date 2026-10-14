# SMART TRAVELLING SHORTEST PATH BOOKING PLATFORM

A Python-based travel planning application that helps users identify efficient routes between locations using graph-based algorithms and supports a convenient travel booking workflow.

## Project Information

- **Course:** 26CS5101E – Computational Thinking and Programming
- **Program:** M.Tech in Artificial Intelligence and Data Science
- **Trimester:** 1
- **Student Name:** SHAIK GOUSE BASHA
- **Student ID:** 2601150020
- **Project Supervisor:** Dr. G. Syam Prasad
- **Academic Year:** 2026–2027
- **Institution:** K L University

## Project Overview

The Smart Travelling Shortest Path Booking Platform is designed to simplify travel planning by finding suitable routes between a source and a destination. It applies computational thinking, Python programming, graph representation, and shortest-path algorithms to identify routes based on criteria such as distance, estimated travel time, or cost.

The project demonstrates how a real-world travel planning problem can be divided into manageable modules and solved using appropriate algorithms, data structures, and software engineering practices.

## Objectives

- Find suitable routes between source and destination locations.
- Apply graph algorithms to identify shortest paths.
- Represent transportation networks using nodes, edges, and weights.
- Organize route and booking information using Python data structures.
- Apply object-oriented and functional programming concepts.
- Analyze algorithm time and space complexity.
- Test route-planning logic and validate application behavior.
- Demonstrate computational thinking and problem-solving techniques.

## Technologies and Concepts

- **Programming Language:** Python
- **Algorithms:** Dijkstra's algorithm and graph-based route planning, where implemented
- **Data Structures:** Lists, dictionaries, sets, tuples, and priority queues
- **Programming Paradigms:** Object-oriented and functional programming
- **Testing:** Pytest, where configured
- **Development Tools:** Git, GitHub, and VS Code

## Key Features

- Source and destination input
- Graph-based transportation network representation
- Shortest-path calculation
- Route comparison using available weights
- Route information display
- Booking workflow support, depending on the implemented features
- Input validation and error handling
- Modular and maintainable Python code

> **Note:** The available features depend on the actual project implementation. Live traffic, real-time transport schedules, and external booking integrations should not be assumed unless they are configured and working.

## Computational Thinking Concepts

### 1. Problem Decomposition
Divides the travel-planning problem into smaller tasks, including input validation, route calculation, route display, and booking operations.

### 2. Abstraction
Represents transportation locations as graph nodes and connections as edges with associated weights.

### 3. Pattern Recognition
Identifies repeated structures in routes, connections, and booking operations to encourage reusable code.

### 4. Algorithm Design
Uses suitable graph algorithms to calculate efficient routes according to the selected optimization criteria.

## Algorithm Complexity

For Dijkstra's algorithm implemented with an adjacency list and a binary heap:

- **Time Complexity:** \(O((V+E)\log V)\)
- **Space Complexity:** \(O(V+E)\) for graph storage, with additional memory required for route-processing data.

Here, `V` represents the number of locations (vertices), and `E` represents the number of connections (edges).

## Project Structure

The repository contains the project source code, documentation, tests, and related academic deliverables. The exact directory structure can be explored through the folders and files in this repository.

## Installation and Execution

1. Clone or download this repository.
2. Open the project directory in Visual Studio Code.
3. Create and activate a Python virtual environment if required.
4. Install the dependencies listed in `requirements.txt`.
5. Follow the instructions in the project's README or documentation to run the application.

Example commands for Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Run the application using the entry point specified in the project documentation. For example, if the application uses `main.py`:

```powershell
python main.py
```

## Testing

If the project is configured with Pytest, run the tests using:

```powershell
pytest
```

Tests can cover shortest-path calculations, valid and invalid inputs, unreachable destinations, and booking-related operations where implemented.

## Project Documentation

This repository also includes academic project materials:

- **Project Report:** `2601150020_DOCUMENTATION.docx`
- **Presentation:** `2601150020_PPT_PRESENATATION.PPTX`

These files contain the project report and presentation prepared for the Computational Thinking and Programming course.

## Future Enhancements

- Real-time traffic information
- Integration with public transportation schedules
- Support for multiple transportation modes
- Alternative route recommendations
- Live booking service integration
- Route visualization using interactive maps
- Improved performance for larger transportation networks

## Conclusion

The Smart Travelling Shortest Path Booking Platform demonstrates the application of computational thinking, graph algorithms, Python programming, and software engineering principles to a practical travel-planning problem. The project provides a foundation for developing more advanced route-planning and booking applications.

## Author

**SHAIK GOUSE BASHA**  
Student ID: `2601150020`  
M.Tech – Artificial Intelligence and Data Science  
K L University

## License

This project was developed for academic purposes as part of the Computational Thinking and Programming course.

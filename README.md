# Cubist Systematic Hackathon: Optimizing AI-driven Strategies 

## 1. Introduction

Yesterday at 6:00 pm, we were given an open-ended prompt to build a chess engine. However, being research-oriented students, we decided to approach the challenge not as a standard software engineering sprint, but as a rigorous quantitative research project. We realized that simply asking a Large Language Model to generate code would yield average results at best. Instead, we wanted to empirically discover the optimal way for human developers to collaborate with AI.

Our plan was to formulate four entirely distinct, AI-driven development strategies and use them in parallel to generate prototype engines. To evaluate them, we built a custom tournament arena to force these prototypes to compete against each other. By treating the prompting methodologies themselves as variables in a measurable experiment, we could systematically evaluate their logic, code stability, and compute efficiency. Only after cross-validating their performance and identifying the statistically superior approach would we use those insights to optimize our final, battle-tested chess engine.

```mermaid
graph TD
    %% Define styles for a quantitative/research aesthetic
    classDef strategy fill:#f9f9f9,stroke:#333,stroke-width:1px;
    classDef arena fill:#e1f5fe,stroke:#0288d1,stroke-width:2px;
    classDef winner fill:#e8f5e9,stroke:#388e3c,stroke-width:2px;
    classDef final fill:#fff3e0,stroke:#f57c00,stroke-width:3px;

    subgraph Phase 1: Parallel AI Development
        direction TB
        S1[Strategy 1:<br>Megaprompt]:::strategy
        S2[Strategy 2:<br>Test-Driven Dev]:::strategy
        S3[Strategy 3:<br>TTT Scaler]:::strategy
        S4[Strategy 4:<br>Simple One-Shot]:::strategy
    end

    AM[Arena Maker:<br>Tournament Infrastructure]:::arena

    subgraph Phase 2: Empirical Evaluation
        Arena{Custom Python<br>Tournament Arena}:::arena
    end

    subgraph Phase 3: Selection & Execution
        Win[Winning Methodology:<br>Megaprompt]:::winner
        Opt[Team Parallel Optimization]:::strategy
        Final((Final Battle-Tested<br>Chess Engine)):::final
    end

    %% Connections
    AM -->|Builds| Arena

    S1 -->|Prototype 1| Arena
    S2 -->|Prototype 2| Arena
    S3 -->|Prototype 3| Arena
    S4 -->|Prototype 4| Arena

    Arena -->|Statistical Cross-Validation| Win
    Win -->|Logic Translation| Opt
    Opt --> Final


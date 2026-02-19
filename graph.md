```mermaid
flowchart LR
    classDef default fill:#333333,stroke:#888,color:#eee;
    classDef activeAgent fill:#1B4D3E,stroke:#4CAF50,stroke-width:2px,color:#fff;
    classDef toolNode fill:#222,stroke:#666,stroke-width:1px,color:#ddd;
    
    n_court_process([court_process])
    n_trial_court([trial_court])
    n_investigators([investigators])
    root([🤖 root])

    subgraph court_process_grp ["court_process (Sequential Agent)"]
        direction TB
        verdict_writer([🤖 verdict_writer])
        t_write_file(["🔧 write_file"]):::toolNode
        verdict_writer -.- t_write_file

        subgraph trial_court_grp ["trial_court (Loop Agent)"]
            direction TB
            judge([🤖 judge])
            t_exit_loop(["🔧 exit_loop"]):::toolNode
            judge -.- t_exit_loop

            subgraph investigators_grp ["investigators (Parallel Agent)"]
                direction TB
                admirer([🤖 admirer]):::activeAgent
                critic([🤖 critic])
                
                t_wiki_research(["🔧 wiki_research"]):::toolNode
                t_set_state(["🔧 set_state"]):::toolNode
                
                admirer -.- t_wiki_research
                admirer -.- t_set_state
                critic -.- t_wiki_research
                critic -.- t_set_state
            end
        end
    end

    n_court_process --> n_investigators
    root --> n_trial_court
    n_trial_court --> n_investigators
    n_trial_court --> verdict_writer
    
    n_investigators --> admirer
    n_investigators --> critic
    
    investigators_grp --> judge
    judge --> n_investigators
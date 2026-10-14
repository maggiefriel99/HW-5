# HW 5 — AI Prompts Log

**Assignment goal:** Build Campus Customs Multi-Agent Operations: an MCP server, a FastAPI backend with a multi-agent team (Boss, Inventory, Accounting, Facilities, Customer Service), and a React dashboard where a human can watch the agents work and approve requests. Every agent uses only `gpt-6-luna` through Portkey.

---

## Problem 1: Vibe Coder Prompts

### Initial Prompt
> Ok this is problem 1: Vibe Coder Prompts. Label this as problem 1. Set up AI_Prompts.md. Put one section for each problem have a section with the problem number and name, the prompt I gave you, and any followup prompts. If there is a followup prompt, add a space to write why I needed the prompt. Also use my portkey api for this and use only gpt-6-luna for every agent (don't use anything else)

### Follow-up Prompts

_None yet._

---

## Problem 2: Study the Campus Customs Database

### Initial Prompt
> Ok this is problem 2: Study the Campus Customs Database. Create a new file from the campus customs db and name it Data/campus_customs_new_db. We will use this as a working copy and update it in later problems. Make sure you understand this database. Start output/harness.md. In this, you'll want to list out the tables, what fields are in each of them, then a concise sentence for each one about why the fields is important. We will be adding to the harness throughout the assignment so make sure it is clean and clearly labeled.

### Follow-up Prompts

_None yet._

---

## Problem 3: Campus Customs Multi-Agent Operations

### Initial Prompt
> Ok this is now problem 3:  Campus Customs Multi-Agent Operations.In mcp_server/ write an mcp server that will use a fast mcp and talk to data/campus_customs_new.db. At this time, it does not need to be connected or run. For the rest of this homework, all of my agents will use tools from this server. right now, can you write three tools that we'll use for my tickets in the database. Make sure to keep the names clean, don't make stuff up, and only use what is in the database. The first tool should be for paying the rent and it should check when and how much the rent is for, the second one should check available inventory, and then the last last should evaluate pricing options for bulk discounts. Please append the harness and add each of my tools and list out explicitly which table it reads, which ticket it works on, and write a detailed and explicit sentence about why this tool is right for that ticket. Be detailed and concise. Also make a short file that explains the purpose of our mcp server, what databases it uses, and the three tools we made call it mcp_server/read.me.

### Follow-up Prompts

#### Follow-up 1
> I will tell you when to write the readme it will probably be in problem 11

***Why I needed this prompt:**
My Ai kept trying to make the readme and gitignore but that comes later in the project

---

## Problem 4: Add the MCP Server and Test Each Tool

### Initial Prompt
> Ok so problem 4: Add the MCP server to vibe coder and test each tool. by running them Test each of the the three tools. For the check rent due tool, pull the results and make sure it matches what is in the leases in the database.  For inventory, pick an item item, run the tool, and then see if the quantity matches what is in the database and for the bulk pricing tool, compare against the ectual tickt, report the out and report the potential options. Make sure to also write out exactly what you find in the database. Then, write output/mcp_smoke.json and save the evidence of these tests. For each tool, write the prompt I gave you to test it, the tool name, and the tool output (make sure it matches the values in data/campus_customs_new.db)

### Follow-up Prompts

#### Follow-up 1
> did you execute on 4

***Why I needed this prompt:**
I closed my computer and disonnected so it said claude didn't execute 4. I wanted it to execute.


#### Follow-up 2
> Also I forgot to mention add my mcp server to this so my coder can call the tools and save the connection json text in mcp.json at the project root then redo the rest  and outputs

***Why I needed this prompt:**
I forgot to tell it do this in my initial test

#### Follow-up 3
> were you able to do the test

***Why I needed this prompt:**
It said it could not execute the tools

#### Follow-up 4
> will i be able to keep this chat memory if i reload

***Why I needed this prompt:**

It said I needed to reload the window for it to call the tools. I wanted to make sure the chat would stayin tact.
#### Follow-up 5
> alright run the tests

I realoaded the window. It could now run the tests.


---

## Problem 5: Build the Agent Team and Grow the MCP Tools

### Initial Prompt
> Problem 5: Build the agent team and grow the MCP tools. I want a 5 agent team the boss should make judgement calls distribute work and manage tickets, inventory should check stock and identify if more orders are needed. it would pass needs for more inventory on to the manager. Accounting should look at cash payments and invoices as well as procing, facilities should deal with things relating to stuff in the leases database or property, and customer service should prepare responses to customer tickets. These agents should all be equipped with gpt 6 luna and use my portkey apI. The agents should communicate with each other so if a ticket seems like it needs a higher level decision bring it to the manager or if it seems to require input from multiple disciplines have them be able to pass it off/collaborate on it. <- feel free to elaborate on responsibilities add ideas and make more specific. In backend/prompts put the agent prompts and make one file per agent. Put the data types in backend/models.py and the agent files under backend/. Add any tools my agents may need  (for example, check inventoiry, check leases, write response email) tothe mcp server so they can work on the tickets. Make sure shop facts come from data/campus and don't invent a second shop tools layer that bypasses mcp. When you write these edits wire them to append output/audit_trail.json and make sure not to wipe as you run. In the audit, you should record the tickets addressed, the agent and tools called, tokens used,  if it delgated/invoked other agents and if the calls were aborted due to safety violations, why. Then for output/harness.md list each agent and mcp tool along w the table the tool uses. Also write a short safety section that describes features a real business would add to keep token usage in check and safely handle real customers and real money then update the mcp_server/readme.md so the tool list matches what I have now

### Follow-up Prompts

#### Follow-up 1
> wait

***Why I needed this prompt:**
It asked me if I wanted to create the backend routes. I wanted it to wiat. 


---

## Problem 6: Plan the Three Tickets

### Initial Prompt
> problem 6: plan the three tickets. Create an html file named output/desk_tickets.html you should be able to double click and open a tab there should be five tabs. We should have one for each ticket then also have a cash and reflection tab that should be blank. In the three tabs for tickets create an expected section and Add three sections named who the boss should call, all the agent delegations I expect and which mcp tools. Also add a section for actual results that we will fill in after a run. Dpn't run yet.

### Follow-up Prompts

#### Follow-up 1
> the table is unnecessary just list the tools

***Why I needed this prompt:**
The AI went overboard with formatting. I wanted it to simplify


---

## Problem 7: Backend Routes

### Initial Prompt
> ok problem 7:backend routes. We're going to make the frontend in the next problem and use fastapi and make the following front end calls: return the three tickets and whether they're open or resolved, take a ticket id and run your agent team on that ticket. return recent agent events ie what the agents said and what tools they used so the board can refresh, approve a payment or purchase after a person clicks approve (agents should only prepare to pay but this route is what should actually change cash), return current checking balance from cash_accounts, reset database to original values when I want a fresh run,  in output/harness.md list each route in just a line this should specify what the route does and the url. also go to the backend folder and run this command uvicorn main:app --reload --port 8000

### Follow-up Prompts

_None yet._


---

## Problem 8: Frontend Dashboard

### Initial Prompt
> Ok now do problem 8: majke the frontend dashboard in frontend/ use react + vite + typescript. It should call the routes I built in problem 7. My board should list all the tickets, let you pock a ticket and start an agent team, show each agent and what they're saying and doing while the ticket runs, mark a ticket resolved when the run finishes, show a summary of what each agent did on the ticket, let a human approve a purchase when asked, show the checking balance (this should go down after an approved pay). Use a crisp white on navy. The agents should be handsome dan. I want each dan have different personalities and have their task status above their heads (maybe as fractions of pizza if that would look good) but the statuse updates should be animate. I want the interface to be three columns w ticket management in the center then on the sides live agent activities and payment approval on the right. Make the financial summary really bold and apparent make it engaging. the front end should talk to the backend at http://localhost:800 on the backend allow the vite page origin in a way that allows the browser to call these routes. The board should start with this command npm run dev <- then write output/design.md in this you should say something along the lines of "I chose to do a bulldog theme because handsome dan invokes joy in the Yale community. Making the agents dans makes the dashboard much more fun and engaging. I chose to have status trackers above the dan agents as pizzas because that is also fun and whimsical and pizza is also a cornerstone of the yale community. I thought the three column apprach would lend itself to readability. I also emphasized financial numbers because the bottom line is quintessential to any business operation <- clean that up a little bit but keep my voice, general sentiments, and structure.

### Follow-up Prompts

#### Follow-up 1
> npm run dev <- ran this and fot an error

***Why I needed this prompt:**

I was troubleshooting my error



---


---

## Problem 9: Resolve the Tickets

### Initial Prompt
> Problem 9: Resolve the tickets. We want to test the agents on three tickets. Before doing this, reset our working database and then note the starting balance. Run all three tickets on the agent system. Then fill in the actual sections of the output/desk_tickets.html. Don't change the expected sections. Also on the cash tab note the starting checking balance, how cash balances changed after the ticket was resolved and why (if it was pay/purchas and then the dollar amount), then the ending checking balance it must match cash_accounts in the working database. make sure the cash math is right. make output/resolved_tickets.json and  for each ticket put the id, final status short outcome, what each agent contributed, and human approvals. Then make output/resolbed_board.html. make it so you can double click  I will use this so I can add screenshots of the react board for my tickets. Also make sure to append real runs to output/audit_trail.json and finish the harness so that it covers the tables, mcp rule, agents, api routes, dashboard and safety rules. This should be readable and tell a manager how our system works.

### Follow-up Prompts

#### Follow-up 1
> (Answer to "How do you want to approve the 4 pending payments/purchases?") do the third option but just to be clear you don't have any access to actual $ rn? if you do pause on this

***Why I needed this prompt:**
It asked me if I wanted to send money. Last week, an AI unprompted went looking through my computer files so I just wanted to double check it could not send actual money.


#### Follow-up 2
> (Shared three screenshots of the React board, one per resolved ticket) <- add these screenshots now

***Why I needed this prompt:**

As part of this problem, I needed screenshots. I could not gather them until the initial prompt ran.
---

## Problem 10: Reflection

### Initial Prompt
> Write in the overall section of the tickets of my html. First write evaluate overall performance: I think my agents did a good job. The way they solved the tickets was logical and deferred to human judgement when necessary. I am satisfied with the way the agents executed and do not think they made superfluos calls. then write how actuals compared to expected: For the first ticket, the actual outcome matched expected for the most part. The key differences are that it did not call one predicted tool (prepar_payment). Also, when creating this system my ai made a safety feature that does not allow for self delegation from an agent so that was blocked (the boss tried to call itself). For the second ticket, actuals matched expected exactly. For the third call, the differences were in tools called (check invoice and list vendors were not called.) The inventory tool was also called twice. The order of agents called also differed slightly. Additionally, there was a cash conflict in terms of approving the orders. I was having claude do the approvals and claude flagged this to me so I told it not to proceed with going in to the red which changed the outcome. then write what would have been simpler: All of these tickets would have been simpler to resolve with one agent with tools. All of these callse were happening in sequences and nothing was happening concurrently so there was no reason for the multi agent team. The boss is particularly ineffective as it's sole purpose is delegation which would be unnecessary if we had one agent. Then write three new problems my agents could solve: If a vendor were to ask about an overdue purchase order, my agents could  solve this problem using almost solely the tools in accounting. If a customer were to ask where the warehouses were, my agent would be able to address this by invoking both the facilites agent and customer service agent (although it is questionable if we would to release this information, I believe my agents would). With the existing tools available, my agent could also be programmed to automatically order new stock when inventory gets low. ok then also wirte three new problems my agent could not solve: My agent would not be able to respond to customer complaints about quality of products for example if the yale logo on a campus customs hoodie was fases, my agent would not at this time be able to prepare campus customs ccounting statements (cashflows, balance sheets, etc). My agent could also not track the shipping status of customer orders which is something our camus customers would likely really want.

### Follow-up Prompts

#### Follow-up 1
> that's problem 10:reflection

***Why I needed this prompt:**


#### Follow-up 2
> also add to the reflection that the sequential thing slows it down but is a safety measure. This could be altered if i were to do further iterations. this should be added to the part where i talked abt how it was sequential

***Why I needed this prompt:**


---

## Problem 11: Submit to GitHub

### Initial Prompt
> Ok so this prompt is problem 11: submit to github. Add a read.me that explains how to copy the original db to the working copy when you need a lean run, how to start mcp server the stat fastapi backend, starting the react board and reseting the db before a full 3 ticket run. Also make sure to add an env.example and don't reveal my actual portkey. The file layout is attached in sc form make it match that. You want to make this so someone could clone it and run it. Double check you can do that in the way it gets uploaded to github. Also make sure to include the data (both sets) Then when everything is good upload to github put it in this repo https://github.com/maggiefriel99/HW-5
>
> (Attached: screenshot of the required file layout.)

### Follow-up Prompts

_None yet._

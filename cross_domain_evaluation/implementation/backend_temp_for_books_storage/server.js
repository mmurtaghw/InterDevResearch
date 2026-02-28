const express = require("express");
const fs = require("fs");
const path = require("path");
const cors = require("cors");

const app = express();
const PORT = 2600;
const DATA_FILE = path.join(__dirname, "books-data.json");

app.use(express.json());
app.use(cors());


const SUMMARY_FILE = path.join(__dirname, "summary-data.json");


// Read JSON file
const readData = () => {
    try {
        if (!fs.existsSync(DATA_FILE)) {
            return {}; // Return an empty object to match the format
        }
        const content = fs.readFileSync(DATA_FILE, "utf8");
        return content ? JSON.parse(content) : {};
    } catch (error) {
        console.error("Error reading data file:", error);
        return {};
    }
};
// Directly overwrite the JSON file
const writeData = (data) => {
    try {
        fs.writeFileSync(DATA_FILE, JSON.stringify(data, null, 2));
    } catch (error) {
        console.error("Error writing data file:", error);
    }
};

// Get book data
app.get("/books", (req, res) => {
    res.json(readData());
});

// // Overwrite and store book data
// app.post("/books", (req, res) => {
//     try {
//         const { lines, nodes, rootId } = req.body;

//         if (!lines || !nodes || !rootId) {
//             return res.status(400).json({ message: "Missing lines, nodes, or rootId in request body" });
//         }

//         // Directly overwrite the JSON file
//         writeData({ lines, nodes, rootId });

//         res.json({ message: "Book data successfully stored" });
//     } catch (error) {
//         console.error("Error storing book data:", error);
//         res.status(500).json({ message: "Internal server error" });
//     }
// });

const APPEND = true; // ✅ Set to true to append, false to overwrite (toggle for debugging)

// Generate unique IDs for new nodes
const generateId = (index) => {
    const chars = "abcdefghijklmnopqrstuvwxyz";
    if (index < 26) return chars[index];
    return chars[Math.floor(index / 26) - 1] + chars[index % 26];
};

// store book data
app.post("/books", (req, res) => {
    try {
        const { lines, nodes, rootId } = req.body;

        if (!lines || !nodes || !rootId) {
            return res.status(400).json({ message: "Missing lines, nodes, or rootId in request body" });
        }

        if (APPEND) {
            const existingData = readData();
            const existingNodes = existingData.nodes || [];
            const nodeOffset = existingNodes.length;

            // Old ID -> New ID
            const idMap = {}; 

            // 1. Rename the `id` and `text` fields in nodes
            const newNodes = nodes.map((node, idx) => {
                const newId = generateId(nodeOffset + idx);
                idMap[node.id] = newId;
                return {
                    ...node,
                    id: newId,
                    text: newId
                };
            });

            // 2. Replace 'from' and 'to' in lines
            const newLines = lines.map(line => ({
                from: idMap[line.from],
                to: idMap[line.to],
                reason: line.reason
            }));

            const mergedData = {
                lines: [...(existingData.lines || []), ...newLines],
                nodes: [...existingNodes, ...newNodes],
                rootId: existingData.rootId || rootId
            };

            writeData(mergedData);
            res.json({ message: "Book data appended with remapped IDs successfully" });
        } else {
            writeData({ lines, nodes, rootId });
            res.json({ message: "Book data successfully stored" });
        }
    } catch (error) {
        console.error("Error storing book data:", error);
        res.status(500).json({ message: "Internal server error" });
    }
});


// Clear book data
app.delete("/books", (req, res) => {
    writeData({ lines: [], nodes: [], rootId: "" });
    res.json({ message: "All book data cleared" });
});

// ✅ NEW: POST /books/node-attribute - get one attribute from one node by ID
app.post("/books/node-attribute", (req, res) => {
    try {
      const { id, attribute } = req.body;
  
      if (!id || !attribute) {
        return res.status(400).json({ message: "Missing 'id' or 'attribute' in request body" });
      }
  
      const data = readData();
      const node = data.nodes?.find(n => n.id === id);
  
      if (!node) {
        return res.status(404).json({ message: `Node with id '${id}' not found` });
      }
  
      const value = node.data?.[attribute];
  
      if (value === undefined) {
        return res.status(404).json({ message: `Attribute '${attribute}' not found in node '${id}'` });
      }
  
      res.json(value); 
    } catch (error) {
      console.error("Error fetching attribute:", error);
      res.status(500).json({ message: "Internal server error" });
    }
  });
  

// Read summaries
const readSummaries = () => {
    try {
        if (!fs.existsSync(SUMMARY_FILE)) {
            return [];
        }
        const content = fs.readFileSync(SUMMARY_FILE, "utf8");
        return content ? JSON.parse(content) : [];
    } catch (error) {
        console.error("Error reading summary file:", error);
        return [];
    }
};

// Append a new summary entry
const appendSummary = (newSummary) => {
    const summaries = readSummaries();
    summaries.push(newSummary);
    fs.writeFileSync(SUMMARY_FILE, JSON.stringify(summaries, null, 2));
};
// API to get all summaries
app.get("/summary", (req, res) => {
    try {
        const summaries = readSummaries();
        res.json(summaries);
    } catch (error) {
        console.error("Error fetching all summaries:", error);
        res.status(500).json({ message: "Internal server error" });
    }
});

// API to add a summary entry
app.post("/summary", (req, res) => {
    try {
        const { summary, summary_title } = req.body;

        if (!summary) {
            return res.status(400).json({ message: "Missing 'summary' in request body" });
        }

        const summaries = readSummaries();
        let baseTitle = summary_title || "Temporary Summary";
        let uniqueTitle = baseTitle;
        let counter = 2;

        while (summaries.find(entry => entry.summary_title === uniqueTitle)) {
            uniqueTitle = `${baseTitle} (${counter})`;
            counter++;
        }

        appendSummary({ summary, summary_title: uniqueTitle });

        res.json({ message: "Summary added successfully", summary_title: uniqueTitle });
    } catch (error) {
        console.error("Error adding summary:", error);
        res.status(500).json({ message: "Internal server error" });
    }
});



// API to get a summary by title
app.get("/summary/:title", (req, res) => {
    try {
        const { title } = req.params;
        const summaries = readSummaries();

        const match = summaries.find(entry => entry.summary_title === title);

        if (!match) {
            return res.status(404).json({ message: `Summary with title '${title}' not found` });
        }

        res.json(match); 
    } catch (error) {
        console.error("Error fetching summary by title:", error);
        res.status(500).json({ message: "Internal server error" });
    }
});

app.delete("/summary/:title", (req, res) => {
    try {
        const { title } = req.params;
        const summaries = readSummaries();

        const filtered = summaries.filter(entry => entry.summary_title !== title);

        if (filtered.length === summaries.length) {
            return res.status(404).json({ message: `Summary titled '${title}' not found` });
        }

        fs.writeFileSync(SUMMARY_FILE, JSON.stringify(filtered, null, 2));
        res.json({ message: `Summary titled '${title}' deleted successfully` });
    } catch (error) {
        console.error("Error deleting summary:", error);
        res.status(500).json({ message: "Internal server error" });
    }
});

app.post("/books/reasons-between", (req, res) => {
    try {
      const { from, to } = req.body;
  
      if (!from || !to) {
        return res.status(400).json({ message: "Missing 'from' or 'to' in request body" });
      }
  
      const data = readData();
      const reasons = data.lines
      .filter(line =>
        (line.from === from && line.to === to) ||
        (line.from === to && line.to === from)
      )
      .map(line => line.reason);
    
  
      res.json({ reasons });
    } catch (error) {
      console.error("Error fetching reasons between nodes:", error);
      res.status(500).json({ message: "Internal server error" });
    }
  });
  

// Start the server
app.listen(PORT, () => {
    console.log(`✅ Server running at http://localhost:${PORT}`);
});

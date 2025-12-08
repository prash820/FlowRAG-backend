echo "=== Monitoring qblock workflow ingestion ==="
echo "Started at: $(date)"
echo ""

MAX_ATTEMPTS=60  # 60 attempts * 30 seconds = 30 minutes max
ATTEMPT=0
LAST_COUNT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    ATTEMPT=$((ATTEMPT + 1))
    
    # Try to get namespaces
    RESPONSE=$(curl -s --max-time 15 http://localhost:8000/api/v1/ingest/namespaces 2>/dev/null)
    
    if [ -n "$RESPONSE" ]; then
        # Parse response and count qblock namespaces
        RESULT=$(echo "$RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    qblock = [n for n in data if 'qblock' in n['name']]
    total_nodes = sum(n.get('node_count', 0) or 0 for n in qblock)
    print(f'{len(qblock)}|{total_nodes}')
    for n in qblock:
        nodes = n.get('node_count', 0) or 0
        print(f\"  {n['name']}: {nodes} nodes\", file=sys.stderr)
except:
    print('0|0')
" 2>&1)
        
        COUNT=$(echo "$RESULT" | head -1 | cut -d'|' -f1)
        TOTAL=$(echo "$RESULT" | head -1 | cut -d'|' -f2)
        DETAILS=$(echo "$RESULT" | tail -n +2)
        
        echo "[$(date +%H:%M:%S)] Attempt $ATTEMPT: $COUNT namespaces, $TOTAL total nodes"
        if [ -n "$DETAILS" ]; then
            echo "$DETAILS"
        fi
        
        # Check if we have all 6 namespaces with data
        if [ "$COUNT" -ge 6 ] && [ "$TOTAL" -gt 0 ]; then
            echo ""
            echo "=== Ingestion Complete! ==="
            echo "All 6 qblock namespaces are now ingested."
            echo "Total nodes: $TOTAL"
            echo "Finished at: $(date)"
            exit 0
        fi
        
        # Track progress
        if [ "$TOTAL" -ne "$LAST_COUNT" ]; then
            LAST_COUNT=$TOTAL
        fi
    else
        echo "[$(date +%H:%M:%S)] Attempt $ATTEMPT: Server busy (no response)"
    fi
    
    sleep 30
done

echo ""
echo "=== Polling timeout ==="
echo "Ingestion may still be in progress. Check manually with:"
echo "curl http://localhost:8000/api/v1/ingest/namespaces"

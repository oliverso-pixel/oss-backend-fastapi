#!/bin/bash
# monitor_redis.sh

while true; do
    clear
    echo "=== Redis Monitor - $(date) ==="
    
    # 基本狀態
    echo -e "\n[連接狀態]"
    redis-cli ping
    
    # 內存使用
    echo -e "\n[內存使用]"
    redis-cli info memory | grep "used_memory_human"
    
    # 客戶端連接
    echo -e "\n[客戶端連接]"
    redis-cli info clients | grep "connected_clients"
    
    # 操作統計
    echo -e "\n[操作統計]"
    redis-cli info stats | grep -E "(total_commands_processed|instantaneous_ops_per_sec)"
    
    # 黑名單統計
    echo -e "\n[黑名單統計]"
    echo "黑名單總數: $(redis-cli scard token:blacklist:all)"
    echo "黑名單鍵數: $(redis-cli keys 'token:blacklist:*' | wc -l)"
    
    sleep 5
done
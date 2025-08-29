package com.example.antigrief;

import org.bukkit.Location;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.block.BlockBreakEvent;
import org.bukkit.event.block.BlockPlaceEvent;
import org.bukkit.event.block.BlockBreakEvent;
import org.bukkit.event.block.BlockPlaceEvent;
import org.bukkit.event.block.TNTPrimeEvent;
import org.bukkit.event.entity.EntityDamageByEntityEvent;
import org.bukkit.event.inventory.InventoryClickEvent;
import org.bukkit.event.player.PlayerBucketEmptyEvent;
import org.bukkit.event.player.PlayerChatEvent;
import org.bukkit.event.player.PlayerInteractEvent;
import org.bukkit.event.player.PlayerMoveEvent;
import org.json.JSONObject;

import java.time.Instant;

public class PlayerEventListener implements Listener {

    private final WebSocketClientManager clientManager;

    public PlayerEventListener(WebSocketClientManager clientManager) {
        this.clientManager = clientManager;
    }

    private JSONObject createBaseEventData(Player player, String eventType) {
        JSONObject data = new JSONObject();
        data.put("timestamp", Instant.now().toString());
        data.put("eventType", eventType);
        data.put("playerUUID", player.getUniqueId().toString());
        data.put("playerName", player.getName());

        Location loc = player.getLocation();
        JSONObject locationData = new JSONObject();
        locationData.put("world", loc.getWorld().getName());
        locationData.put("x", loc.getX());
        locationData.put("y", loc.getY());
        locationData.put("z", loc.getZ());
        data.put("playerLocation", locationData);

        return data;
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onPlayerMove(PlayerMoveEvent event) {
        if (event.getFrom().getBlockX() != event.getTo().getBlockX() ||
            event.getFrom().getBlockY() != event.getTo().getBlockY() ||
            event.getFrom().getBlockZ() != event.getTo().getBlockZ()) {

            JSONObject data = createBaseEventData(event.getPlayer(), "PlayerMove");
            clientManager.sendEventData(data);
        }
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onBlockBreak(BlockBreakEvent event) {
        JSONObject data = createBaseEventData(event.getPlayer(), "BlockBreak");

        Location loc = event.getBlock().getLocation();
        JSONObject blockData = new JSONObject();
        blockData.put("type", event.getBlock().getType().toString());
        blockData.put("world", loc.getWorld().getName());
        blockData.put("x", loc.getBlockX());
        blockData.put("y", loc.getBlockY());
        blockData.put("z", loc.getBlockZ());
        data.put("block", blockData);

        clientManager.sendEventData(data);
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onBlockPlace(BlockPlaceEvent event) {
        JSONObject data = createBaseEventData(event.getPlayer(), "BlockPlace");

        Location loc = event.getBlock().getLocation();
        JSONObject blockData = new JSONObject();
        blockData.put("type", event.getBlock().getType().toString());
        blockData.put("world", loc.getWorld().getName());
        blockData.put("x", loc.getBlockX());
        blockData.put("y", loc.getBlockY());
        blockData.put("z", loc.getBlockZ());
        data.put("block", blockData);

        clientManager.sendEventData(data);
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onPlayerInteract(PlayerInteractEvent event) {
        JSONObject data = createBaseEventData(event.getPlayer(), "PlayerInteract");
        data.put("action", event.getAction().toString());
        if (event.hasItem()) {
            data.put("itemInHand", event.getItem().getType().toString());
        }
        if (event.hasBlock()) {
            Location loc = event.getClickedBlock().getLocation();
            JSONObject blockData = new JSONObject();
            blockData.put("type", event.getClickedBlock().getType().toString());
            blockData.put("world", loc.getWorld().getName());
            blockData.put("x", loc.getBlockX());
            blockData.put("y", loc.getBlockY());
            blockData.put("z", loc.getBlockZ());
            data.put("clickedBlock", blockData);
        }
        clientManager.sendEventData(data);
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onBucketEmpty(PlayerBucketEmptyEvent event) {
        JSONObject data = createBaseEventData(event.getPlayer(), "PlayerBucketEmpty");
        data.put("bucket", event.getBucket().toString());
        Location loc = event.getBlock().getLocation();
        JSONObject blockData = new JSONObject();
        blockData.put("world", loc.getWorld().getName());
        blockData.put("x", loc.getBlockX());
        blockData.put("y", loc.getBlockY());
        blockData.put("z", loc.getBlockZ());
        data.put("location", blockData);
        clientManager.sendEventData(data);
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onPlayerChat(PlayerChatEvent event) {
        JSONObject data = createBaseEventData(event.getPlayer(), "PlayerChat");
        data.put("message", event.getMessage());
        clientManager.sendEventData(data);
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onInventoryClick(InventoryClickEvent event) {
        // Ignore clicks in player's own inventory to reduce noise
        if (event.getClickedInventory() != null && event.getClickedInventory().getHolder() instanceof Player) {
            return;
        }

        JSONObject data = createBaseEventData((Player) event.getWhoClicked(), "InventoryClick");
        if (event.getClickedInventory() != null && event.getClickedInventory().getType() != null) {
            data.put("inventoryType", event.getClickedInventory().getType().toString());
        }
        if (event.getCurrentItem() != null) {
            data.put("item", event.getCurrentItem().getType().toString());
        }
        data.put("action", event.getAction().toString());
        clientManager.sendEventData(data);
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onEntityDamage(EntityDamageByEntityEvent event) {
        if (!(event.getDamager() instanceof Player)) {
            return; // Only track damage caused by players
        }
        Player damager = (Player) event.getDamager();
        JSONObject data = createBaseEventData(damager, "EntityDamageByEntity");
        data.put("damagedEntity", event.getEntityType().toString());
        data.put("damage", event.getDamage());

        Location loc = event.getEntity().getLocation();
        JSONObject locationData = new JSONObject();
        locationData.put("world", loc.getWorld().getName());
        locationData.put("x", loc.getX());
        locationData.put("y", loc.getY());
        locationData.put("z", loc.getZ());
        data.put("location", locationData);

        clientManager.sendEventData(data);
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onTntPrime(TNTPrimeEvent event) {
        // Find the player who might have caused this
        if (event.getPrimingEntity() instanceof Player) {
            Player player = (Player) event.getPrimingEntity();
            JSONObject data = createBaseEventData(player, "TNTPrime");

            Location loc = event.getBlock().getLocation();
            JSONObject locationData = new JSONObject();
            locationData.put("world", loc.getWorld().getName());
            locationData.put("x", loc.getX());
            locationData.put("y", loc.getY());
            locationData.put("z", loc.getZ());
            data.put("location", locationData);

            clientManager.sendEventData(data);
        }
    }
}

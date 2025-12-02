"""
Player profile view showing stats, inventory, and progress.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QTableWidget, QTableWidgetItem, QGroupBox, QHeaderView, QPushButton, QWidget, QTabWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from data.repositories import ItemRepository, RepoWorldRepository, QuestRepository, PlayerRepository
from game.state import get_game_state
from game.logic import calculate_inventory_space, apply_item_stats
from core.logging_utils import get_logger
from core.config import get_resource_path

logger = get_logger(__name__)

class PlayerView(QWidget):
    """
    Player profile view.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Player Profile")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)
        
        # Create tab widget
        self.tabs = QTabWidget()
        
        # Stats tab
        stats_tab = QWidget()
        stats_tab_layout = QHBoxLayout()
        
        # Left column: Stats content
        stats_left_layout = QVBoxLayout()
        
        self.name_label = QLabel("Name: -")
        self.level_label = QLabel("Level: -")
        self.xp_label = QLabel("XP: -")
        self.xp_bar = QProgressBar()
        self.xp_bar.setMaximum(100)
        # Set XP bar color to yellow
        self.xp_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #333;
                border-radius: 3px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #FFC107;
                border-radius: 2px;
            }
        """)
        
        self.hp_label = QLabel("HP: -")
        self.attack_label = QLabel("Attack: -")
        self.defense_label = QLabel("Defense: -")
        self.speed_label = QLabel("Speed: -")
        self.luck_label = QLabel("Luck: -")
        
        stats_left_layout.addWidget(self.name_label)
        stats_left_layout.addWidget(self.level_label)
        stats_left_layout.addWidget(self.xp_label)
        stats_left_layout.addWidget(self.xp_bar)
        stats_left_layout.addWidget(QLabel("---"))
        stats_left_layout.addWidget(self.hp_label)
        stats_left_layout.addWidget(self.attack_label)
        stats_left_layout.addWidget(self.defense_label)
        stats_left_layout.addWidget(self.speed_label)
        stats_left_layout.addWidget(self.luck_label)
        stats_left_layout.addStretch()
        
        # Right column: Player image
        stats_right_layout = QVBoxLayout()
        stats_right_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        
        self.player_image = QLabel()
        self.player_image.setFixedSize(96, 96)
        self.player_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.player_image.setStyleSheet("background-color: transparent;")
        stats_right_layout.addWidget(self.player_image)
        stats_right_layout.addStretch()
        
        stats_tab_layout.addLayout(stats_left_layout, stretch=1)
        stats_tab_layout.addLayout(stats_right_layout, stretch=0)
        stats_tab.setLayout(stats_tab_layout)
        
        # Inventory tab
        inventory_tab = QWidget()
        inventory_tab_layout = QVBoxLayout()
        
        # Inventory space label
        self.inventory_space_label = QLabel("Inventory: 0/10")
        inventory_tab_layout.addWidget(self.inventory_space_label)
        
        # Recycler button
        recycler_btn = QPushButton("Open Recycler")
        recycler_btn.clicked.connect(self.open_recycler)
        inventory_tab_layout.addWidget(recycler_btn)
        
        self.inventory_table = QTableWidget()
        self.inventory_table.setColumnCount(6)
        self.inventory_table.setHorizontalHeaderLabels(["Name", "Rarity", "Bonuses", "Quantity", "Equipped", "Actions"])
        
        # Set column widths - make Bonuses column wider
        header = self.inventory_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Name
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Rarity
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)  # Bonuses - resizable
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Quantity
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Equipped
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Actions
        
        # Set minimum width for Bonuses column
        self.inventory_table.setColumnWidth(2, 250)  # Bonuses column default width
        
        # Allow last section to stretch
        header.setStretchLastSection(False)
        
        inventory_tab_layout.addWidget(self.inventory_table)
        inventory_tab.setLayout(inventory_tab_layout)
        
        # Achievements tab
        achievements_tab = QWidget()
        achievements_tab_layout = QVBoxLayout()
        
        self.achievements_label = QLabel("No achievements yet")
        self.achievements_label.setWordWrap(True)
        achievements_tab_layout.addWidget(self.achievements_label)
        achievements_tab_layout.addStretch()
        achievements_tab.setLayout(achievements_tab_layout)
        
        # Add tabs
        self.tabs.addTab(stats_tab, "Stats")
        self.tabs.addTab(inventory_tab, "Inventory")
        self.tabs.addTab(achievements_tab, "Achievements")
        
        layout.addWidget(self.tabs)
        self.setLayout(layout)
    
    def refresh(self):
        """Refresh player data."""
        game_state = get_game_state()
        player = game_state.current_player
        
        if not player:
            self.name_label.setText("Name: No player selected")
            self.load_player_image(None)
            return
        
        # Update stats
        self.name_label.setText(f"Name: {player.name}")
        self.level_label.setText(f"Level: {player.level}")
        self.xp_label.setText(f"XP: {player.xp} / {player.level * 100}")
        self.xp_bar.setMaximum(player.level * 100)
        self.xp_bar.setValue(player.xp)
        
        # Load player image
        self.load_player_image(player)
        
        # Calculate stats with equipped items
        base_hp = player.hp
        base_attack = player.attack
        base_defense = player.defense
        base_speed = player.speed
        base_luck = player.luck
        
        inventory = ItemRepository.get_player_inventory(player.id)
        equipped_bonuses = {"hp": 0, "attack": 0, "defense": 0, "speed": 0, "luck": 0}
        
        for item, quantity, equipped in inventory:
            if equipped:
                bonuses = item.get_stat_bonuses()
                for stat, bonus in bonuses.items():
                    if stat in equipped_bonuses:
                        equipped_bonuses[stat] += bonus
        
        # Display stats with bonuses
        total_hp = base_hp + equipped_bonuses["hp"]
        total_attack = base_attack + equipped_bonuses["attack"]
        total_defense = base_defense + equipped_bonuses["defense"]
        total_speed = base_speed + equipped_bonuses["speed"]
        total_luck = base_luck + equipped_bonuses["luck"]
        
        self.hp_label.setText(f"HP: {total_hp} ({base_hp} + {equipped_bonuses['hp']})")
        self.attack_label.setText(f"Attack: {total_attack} ({base_attack} + {equipped_bonuses['attack']})")
        self.defense_label.setText(f"Defense: {total_defense} ({base_defense} + {equipped_bonuses['defense']})")
        self.speed_label.setText(f"Speed: {total_speed} ({base_speed} + {equipped_bonuses['speed']})")
        self.luck_label.setText(f"Luck: {total_luck} ({base_luck} + {equipped_bonuses['luck']})")
        
        # Update inventory space
        inventory_count = ItemRepository.get_inventory_count(player.id)
        max_inventory = calculate_inventory_space(player.level)
        self.inventory_space_label.setText(f"Inventory: {inventory_count}/{max_inventory}")
        
        # Update inventory table
        self.inventory_table.setRowCount(0)
        
        for item, quantity, equipped in inventory:
            row = self.inventory_table.rowCount()
            self.inventory_table.insertRow(row)
            
            # Name
            name_text = item.name
            if equipped:
                name_text += " [EQUIPPED]"
            self.inventory_table.setItem(row, 0, QTableWidgetItem(name_text))
            
            # Rarity
            self.inventory_table.setItem(row, 1, QTableWidgetItem(item.rarity))
            
            # Bonuses
            bonuses = item.get_stat_bonuses()
            bonuses_str = ", ".join([f"{k}: +{v}" for k, v in bonuses.items()])
            self.inventory_table.setItem(row, 2, QTableWidgetItem(bonuses_str))
            
            # Quantity
            self.inventory_table.setItem(row, 3, QTableWidgetItem(str(quantity)))
            
            # Equipped status
            self.inventory_table.setItem(row, 4, QTableWidgetItem("Yes" if equipped else "No"))
            
            # Actions (Equip/Unequip button)
            action_widget = QWidget()
            action_layout = QHBoxLayout()
            action_layout.setContentsMargins(2, 2, 2, 2)
            
            if equipped:
                unequip_btn = QPushButton("Unequip")
                unequip_btn.clicked.connect(lambda checked, item_id=item.id: self.unequip_item(item_id))
                action_layout.addWidget(unequip_btn)
            else:
                equip_btn = QPushButton("Equip")
                equip_btn.clicked.connect(lambda checked, item_id=item.id: self.equip_item(item_id))
                action_layout.addWidget(equip_btn)
            
            action_widget.setLayout(action_layout)
            self.inventory_table.setCellWidget(row, 5, action_widget)
        
        # Update achievements
        worlds = RepoWorldRepository.get_all()
        completed_quests = sum(1 for w in worlds for q in QuestRepository.get_by_world_id(w.id) if q.status == "completed")
        
        achievements = []
        achievements.append(f"Worlds Discovered: {len(worlds)}")
        achievements.append(f"Quests Completed: {completed_quests}")
        
        self.achievements_label.setText("\n".join(achievements))
    
    def load_player_image(self, player):
        """Load and display the player character image."""
        if player and player.player_image_id:
            # Format image ID as 001, 002, etc.
            image_id_str = f"{player.player_image_id:03d}"
            image_path = get_resource_path(f"assets/player/{image_id_str}.png")
            
            if image_path.exists():
                pixmap = QPixmap(str(image_path))
                # Scale to 96x96 while maintaining aspect ratio
                scaled_pixmap = pixmap.scaled(96, 96, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.player_image.setPixmap(scaled_pixmap)
            else:
                logger.warning(f"Player image not found: {image_path}")
                self.player_image.clear()
        else:
            # Clear image if no player or no image ID
            self.player_image.clear()
    
    def equip_item(self, item_id: int):
        """Equip an item."""
        game_state = get_game_state()
        if not game_state.current_player:
            return
        
        ItemRepository.equip_item(game_state.current_player.id, item_id)
        self.refresh()
    
    def unequip_item(self, item_id: int):
        """Unequip an item."""
        game_state = get_game_state()
        if not game_state.current_player:
            return
        
        ItemRepository.unequip_item(game_state.current_player.id, item_id)
        self.refresh()
    
    def open_recycler(self):
        """Open the recycler dialog."""
        from ui.widgets.recycler_dialog import RecyclerDialog
        dialog = RecyclerDialog(self)
        dialog.exec()
        # Refresh after closing recycler
        self.refresh()


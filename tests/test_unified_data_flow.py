#!/usr/bin/env python3
"""
Test suite to verify unified data flow across all dashboard components.
Ensures mini-cards and main cards both read from identical `self.data` source.
"""
import unittest
import tkinter as tk
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import main


class UnifiedDataFlowTest(unittest.TestCase):
    def setUp(self):
        self.app = main.App()
        self.app.withdraw()
        self.app.update_idletasks()

    def tearDown(self):
        if self.app.winfo_exists():
            self.app.destroy()

    def test_quick_metrics_receive_data_from_unified_source(self):
        """Verify quick metrics cards update from self.data"""
        test_data = {
            'cpu': {'name': 'Intel Core i7', 'usage': 65, 'temperature': 72},
            'memory': {'total': '32 GB', 'used': '16 GB', 'free': '16 GB', 'percent': 50},
            'disks': [{
                'model': 'Samsung 970 EVO',
                'name': '/dev/sda',
                'total': '1000 GB',
                'used': '650 GB',
                'free': '350 GB',
                'temperature': 48,
                'smart_health': 98
            }],
            'system': {'os_name': 'Windows 11', 'version': '24H2'},
        }
        
        self.app.data = test_data
        self.app._render_dashboard(test_data)
        self.app.update_idletasks()
        
        # Check CPU temperature metric
        cpu_temp_label = self.app.quick_metrics['cpu_temp']['value']
        self.assertIn('72', cpu_temp_label.cget('text'))
        
        # Check CPU usage metric
        cpu_usage_label = self.app.quick_metrics['cpu_usage']['value']
        self.assertIn('65', cpu_usage_label.cget('text'))
        
        # Check RAM usage metric
        ram_usage_label = self.app.quick_metrics['ram_usage']['value']
        self.assertIn('50', ram_usage_label.cget('text'))
        
        # Check SSD temperature metric
        ssd_temp_label = self.app.quick_metrics['ssd_temp']['value']
        self.assertIn('48', ssd_temp_label.cget('text'))
        
        # Check SSD health metric
        ssd_health_label = self.app.quick_metrics['ssd_health']['value']
        self.assertIn('98', ssd_health_label.cget('text'))

    def test_main_cards_receive_data_from_unified_source(self):
        """Verify main cards update from self.data"""
        test_data = {
            'cpu': {'name': 'Intel Core i7-13700KF', 'usage': 45, 'temperature': 58},
            'memory': {'total': '32 GB', 'used': '8 GB', 'free': '24 GB', 'percent': 25},
            'disks': [{
                'model': 'Samsung 970 EVO',
                'name': '/dev/sda',
                'total': '1000 GB',
                'used': '400 GB',
                'free': '600 GB',
                'temperature': 42,
                'smart_health': 95
            }],
            'system': {'os_name': 'Windows 11', 'version': '24H2'},
        }
        
        self.app.data = test_data
        self.app._render_dashboard(test_data)
        self.app.update_idletasks()
        
        # Check CPU card
        self.assertEqual(self.app.lbl_cpu_name.cget('text'), 'Intel Core i7-13700KF')
        self.assertIn('58', self.app.lbl_cpu_temp.cget('text'))
        self.assertIn('45', self.app.lbl_cpu_usage.cget('text'))
        
        # Check RAM card
        self.assertEqual(self.app.lbl_ram_total.cget('text'), '32 GB')
        self.assertIn('25', self.app.lbl_ram_usage.cget('text'))
        
        # Check SSD card (health label is formatted text, not percentage)
        self.assertIn('Samsung', self.app.lbl_ssd_model.cget('text'))
        self.assertIn('42', self.app.lbl_ssd_temp.cget('text'))
        # Health shows as "Excelente", "Boa", etc. not the raw percentage
        health_text = self.app.lbl_ssd_health.cget('text').lower()
        self.assertIn(health_text, ['excelente', 'boa', 'aceitável', 'ruim', 'crítico'])

    def test_mini_cards_and_main_cards_show_identical_values(self):
        """Verify mini-cards and main-cards display values from the same data source"""
        test_data = {
            'cpu': {'name': 'Test CPU', 'usage': 55, 'temperature': 65},
            'memory': {'total': '16 GB', 'used': '8 GB', 'free': '8 GB', 'percent': 50},
            'disks': [{
                'model': 'Test SSD',
                'total': '500 GB',
                'used': '250 GB',
                'free': '250 GB',
                'temperature': 45,
                'smart_health': 90
            }],
            'system': {'os_name': 'Windows 11', 'version': '24H2'},
        }
        
        self.app.data = test_data
        self.app._render_dashboard(test_data)
        self.app.update_idletasks()
        
        # Extract values from mini-cards
        mini_cpu_usage = self.app.quick_metrics['cpu_usage']['value'].cget('text').replace('%', '')
        mini_cpu_temp = self.app.quick_metrics['cpu_temp']['value'].cget('text').replace('°C', '')
        mini_ram_usage = self.app.quick_metrics['ram_usage']['value'].cget('text').replace('%', '')
        mini_ssd_temp = self.app.quick_metrics['ssd_temp']['value'].cget('text').replace('°C', '')
        mini_ssd_health = self.app.quick_metrics['ssd_health']['value'].cget('text').replace('%', '')
        
        # Extract values from main-cards
        main_cpu_usage = self.app.lbl_cpu_usage.cget('text').replace('%', '')
        main_cpu_temp = self.app.lbl_cpu_temp.cget('text').replace('°C', '')
        main_ram_usage = self.app.lbl_ram_usage.cget('text').replace('%', '')
        main_ssd_temp = self.app.lbl_ssd_temp.cget('text').replace('°C', '')
        
        # Compare numeric values (should be identical)
        self.assertEqual(mini_cpu_usage.strip(), main_cpu_usage.strip(), 
                        f"CPU usage mismatch: mini={mini_cpu_usage} vs main={main_cpu_usage}")
        self.assertEqual(float(mini_cpu_temp.strip()), float(main_cpu_temp.strip()), 
                        f"CPU temp mismatch: mini={mini_cpu_temp} vs main={main_cpu_temp}")
        self.assertEqual(mini_ram_usage.strip(), main_ram_usage.strip(), 
                        f"RAM usage mismatch: mini={mini_ram_usage} vs main={main_ram_usage}")
        self.assertEqual(float(mini_ssd_temp.strip()), float(main_ssd_temp.strip()), 
                        f"SSD temp mismatch: mini={mini_ssd_temp} vs main={main_ssd_temp}")
        # SSD Health uses different formats: mini shows "90%" while main shows "Boa" (formatted label)
        # Both derive from the same smart_health value (90), so this is expected behavior
        self.assertIn('90', mini_ssd_health.strip(), 
                     f"Mini SSD health should contain '90': {mini_ssd_health}")
        # Main card health is a formatted label (Excelente/Boa/Aceitável/Ruim/Crítico), not numeric

    def test_progress_bars_display_correct_values(self):
        """Verify progress bars are updated with correct percentages"""
        test_data = {
            'cpu': {'name': 'Test CPU', 'usage': 75, 'temperature': 80},
            'memory': {'total': '16 GB', 'percent': 87},
            'disks': [{
                'model': 'Test SSD',
                'total': '500 GB',
                'used': 450,  # 90% usage
                'temperature': 60,
            }],
            'system': {'os_name': 'Windows 11'},
        }
        
        self.app.data = test_data
        self.app._render_dashboard(test_data)
        self.app.update_idletasks()
        
        # Check progress bar text contains percentages (not the default "0%")
        cpu_usage_text = self.app.progress_cpu_usage.itemcget(self.app.progress_cpu_usage.text, 'text')
        ram_usage_text = self.app.progress_ram_usage.itemcget(self.app.progress_ram_usage.text, 'text')
        cpu_temp_text = self.app.progress_cpu_temp.itemcget(self.app.progress_cpu_temp.text, 'text')
        ssd_usage_text = self.app.progress_ssd_usage.itemcget(self.app.progress_ssd_usage.text, 'text')
        
        # Verify percentages are realistic (not all 0%)
        self.assertIn('75', cpu_usage_text, "CPU usage progress should show 75%")
        self.assertIn('87', ram_usage_text, "RAM usage progress should show 87%")
        self.assertIn('80', cpu_temp_text, "CPU temp progress should show 80")
        self.assertIn('90', ssd_usage_text, "SSD usage progress should show 90%")

    def test_data_persistence_across_multiple_renders(self):
        """Verify self.data persists and updates correctly across multiple render cycles"""
        data1 = {
            'cpu': {'name': 'CPU1', 'usage': 30, 'temperature': 50},
            'memory': {'total': '8 GB', 'percent': 40},
            'disks': [{
                'model': 'SSD1',
                'used': '100 GB',
                'total': '500 GB',
                'temperature': 40,
                'smart_health': 100
            }],
            'system': {'os_name': 'Windows 11'},
        }
        
        data2 = {
            'cpu': {'name': 'CPU2', 'usage': 70, 'temperature': 85},
            'memory': {'total': '16 GB', 'percent': 75},
            'disks': [{
                'model': 'SSD2',
                'used': '400 GB',
                'total': '500 GB',
                'temperature': 60,
                'smart_health': 85
            }],
            'system': {'os_name': 'Windows 11'},
        }
        
        # First render
        self.app.data = data1
        self.app._render_dashboard(data1)
        self.app.update_idletasks()
        first_cpu_name = self.app.lbl_cpu_name.cget('text')
        
        # Second render
        self.app.data = data2
        self.app._render_dashboard(data2)
        self.app.update_idletasks()
        second_cpu_name = self.app.lbl_cpu_name.cget('text')
        
        # Verify data changed
        self.assertEqual(first_cpu_name, 'CPU1')
        self.assertEqual(second_cpu_name, 'CPU2')
        self.assertNotEqual(first_cpu_name, second_cpu_name)


if __name__ == '__main__':
    unittest.main()

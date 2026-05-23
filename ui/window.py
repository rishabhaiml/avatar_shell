import sys
import os
import subprocess
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('WebKit', '6.0')
try:
    gi.require_version('Gtk4LayerShell', '1.0')
    from gi.repository import Gtk4LayerShell
except ValueError:
    Gtk4LayerShell = None

from gi.repository import Gtk, Gdk, GLib, WebKit
import config

class AvatarApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="tech.codenxtlab.bhai")
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.drag_start_margin_right = 20
        self.drag_start_margin_bottom = 20

    def do_activate(self):
        self.window = Gtk.ApplicationWindow(application=self)
        self.window.set_default_size(300, 400)
        self.window.set_title("B.H.A.I. Shell")
        self.window.set_decorated(False)

        # Setup modern Wayland Layer Shell bindings if supported on environment
        if Gtk4LayerShell and Gtk4LayerShell.is_supported():
            Gtk4LayerShell.init_for_window(self.window)
            Gtk4LayerShell.set_layer(self.window, Gtk4LayerShell.Layer.OVERLAY)
            Gtk4LayerShell.set_anchor(self.window, Gtk4LayerShell.Edge.BOTTOM, True)
            Gtk4LayerShell.set_anchor(self.window, Gtk4LayerShell.Edge.RIGHT, True)
            Gtk4LayerShell.set_margin(self.window, Gtk4LayerShell.Edge.BOTTOM, 20)
            Gtk4LayerShell.set_margin(self.window, Gtk4LayerShell.Edge.RIGHT, 20)

        # Baseline translucent CSS provider to prevent hover dropout issues
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"window { background-color: rgba(0, 0, 0, 0.01); }")
        Gtk.StyleContext.add_provider_for_display(self.window.get_display(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        # Premium Glassmorphic style sheet for overlay toolbar
        self.toolbar_css = Gtk.CssProvider()
        self.toolbar_css.load_from_data(b"""
            .custom-toolbar {
                background-color: rgba(30, 30, 40, 0.75);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                padding: 4px;
                margin: 10px;
                transition: opacity 0.25s cubic-bezier(0.4, 0, 0.2, 1);
            }
            .toolbar-btn {
                background: transparent;
                border: none;
                border-radius: 6px;
                color: #ffffff;
                padding: 6px 10px;
                font-size: 14px;
                min-width: 32px;
                min-height: 32px;
            }
            .toolbar-btn:hover {
                background-color: rgba(255, 255, 255, 0.15);
                color: #e2e8f0;
            }
            .toolbar-close-btn {
                color: #ef4444;
            }
            .toolbar-close-btn:hover {
                background-color: rgba(239, 68, 68, 0.2);
                color: #f87171;
            }
        """)
        Gtk.StyleContext.add_provider_for_display(self.window.get_display(), self.toolbar_css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        # Webview configuration
        settings = WebKit.Settings()
        settings.set_enable_webgl(True)
        self.webview = WebKit.WebView(settings=settings)
        rgba = Gdk.RGBA()
        rgba.parse("rgba(0, 0, 0, 0)")
        self.webview.set_background_color(rgba)
        
        # Load local webserver URL (falling back to a static offline styled page if needed)
        self.webview.load_uri("http://127.0.0.1:8000/index.html")

        # Create overlay stack to house the Webview and Custom Toolbar cleanly
        self.main_overlay = Gtk.Overlay.new()
        self.main_overlay.set_child(self.webview)

        # Build custom glassmorphic overlay toolbar
        self.custom_toolbar_box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 6)
        self.custom_toolbar_box.add_css_class("custom-toolbar")
        self.custom_toolbar_box.set_opacity(0.0)
        self.custom_toolbar_box.set_halign(Gtk.Align.END)
        self.custom_toolbar_box.set_valign(Gtk.Align.START)

        settings_btn = Gtk.Button.new_with_label("⚙️")
        settings_btn.add_css_class("toolbar-btn")
        
        close_btn = Gtk.Button.new_with_label("❌")
        close_btn.add_css_class("toolbar-btn")
        close_btn.add_css_class("toolbar-close-btn")

        self.custom_toolbar_box.append(settings_btn)
        self.custom_toolbar_box.append(close_btn)

        # Wire settings button event action to launch browser admin view
        def on_settings_clicked(btn):
            print("⚙️ Settings opened. Opening UI dashboard in system browser...")
            subprocess.Popen(["xdg-open", "http://127.0.0.1:8000"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        settings_btn.connect("clicked", on_settings_clicked)

        # Wire close button event to safely shut down the window session
        close_btn.connect("clicked", lambda btn: self.window.close())

        self.main_overlay.add_overlay(self.custom_toolbar_box)
        self.window.set_child(self.main_overlay)
        self.window.present()

        # Connect motion controllers to toggle toolbar visibility on mouse hover
        motion_ctrl = Gtk.EventControllerMotion.new()
        self.main_overlay.add_controller(motion_ctrl)
        motion_ctrl.connect("enter", self.reveal_custom_toolbar)
        motion_ctrl.connect("leave", self.hide_custom_toolbar)

        # Connect Gesture Drag Controller to Webview to handle borderless window moves smoothly
        self.drag_controller = Gtk.GestureDrag.new()
        self.drag_controller.set_button(1)
        self.drag_controller.connect("drag-begin", self.on_drag_begin)
        self.drag_controller.connect("drag-update", self.on_drag_update)
        self.drag_controller.connect("drag-end", self.on_drag_end)
        self.webview.add_controller(self.drag_controller)

    def reveal_custom_toolbar(self, controller, x, y):
        self.custom_toolbar_box.set_opacity(1.0)

    def hide_custom_toolbar(self, controller):
        self.custom_toolbar_box.set_opacity(0.0)

    def on_drag_begin(self, gesture, start_x, start_y):
        if Gtk4LayerShell and Gtk4LayerShell.is_supported():
            self.drag_start_margin_right = Gtk4LayerShell.get_margin(self.window, Gtk4LayerShell.Edge.RIGHT)
            self.drag_start_margin_bottom = Gtk4LayerShell.get_margin(self.window, Gtk4LayerShell.Edge.BOTTOM)
        else:
            # Fallback for standard top-level windows: start interactive drag
            event = gesture.get_current_event()
            device = event.get_device() if event else None
            button = gesture.get_current_button()
            timestamp = event.get_time() if event else 0
            surface = self.window.get_native().get_surface()
            if surface and device:
                try:
                    surface.begin_move(device, button, start_x, start_y, timestamp)
                except Exception as e:
                    print(f"Error starting native move: {e}")

    def on_drag_update(self, gesture, offset_x, offset_y):
        if Gtk4LayerShell and Gtk4LayerShell.is_supported():
            # Coordinate tracking delta adjustments relative to bottom-right anchors:
            # dragging left/up increases margins, dragging right/down decreases margins
            new_margin_right = self.drag_start_margin_right - offset_x
            new_margin_bottom = self.drag_start_margin_bottom - offset_y
            Gtk4LayerShell.set_margin(self.window, Gtk4LayerShell.Edge.RIGHT, int(new_margin_right))
            Gtk4LayerShell.set_margin(self.window, Gtk4LayerShell.Edge.BOTTOM, int(new_margin_bottom))

    def on_drag_end(self, gesture, offset_x, offset_y):
        if Gtk4LayerShell and Gtk4LayerShell.is_supported():
            # Update base drag parameters at the end of window dragging interaction cycle to prevent offset drift
            self.drag_start_margin_right = Gtk4LayerShell.get_margin(self.window, Gtk4LayerShell.Edge.RIGHT)
            self.drag_start_margin_bottom = Gtk4LayerShell.get_margin(self.window, Gtk4LayerShell.Edge.BOTTOM)

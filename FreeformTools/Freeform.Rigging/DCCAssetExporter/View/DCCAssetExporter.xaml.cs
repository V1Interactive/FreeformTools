namespace Freeform.Rigging.DCCAssetExporter
{
    using System;
    using System.ComponentModel;
    using System.Windows;
    using System.Diagnostics;
    using System.Windows.Interop;


    /// <summary>
    /// Interaction logic for DCCAssetExporter.xaml
    /// </summary>
    public partial class DCCAssetExporter : Window
    {
        public DCCAssetExporter()
        {
            InitializeComponent();
            SetupWindow();
            SetupDataContext();
        }

        public DCCAssetExporter(Process parent)
        {
            InitializeComponent();

            WindowInteropHelper helper = new WindowInteropHelper(this);
            helper.Owner = parent.MainWindowHandle;

            SetupWindow();
            SetupDataContext(parent);
        }

        private void DCCAssetExporter_Closing(object sender, System.ComponentModel.CancelEventArgs e)
        {
            if (WindowState == WindowState.Maximized)
            {
                // Use the RestoreBounds as the current values will be 0, 0 and the size of the screen
                Properties.Settings.Default.ExporterTop = RestoreBounds.Top;
                Properties.Settings.Default.ExporterLeft = RestoreBounds.Left;
                Properties.Settings.Default.ExporterHeight = RestoreBounds.Height;
                Properties.Settings.Default.ExporterWidth = RestoreBounds.Width;
                Properties.Settings.Default.ExporterMaximized = true;
            }
            else
            {
                Properties.Settings.Default.ExporterTop = Top;
                Properties.Settings.Default.ExporterLeft = Left;
                Properties.Settings.Default.ExporterHeight = Height;
                Properties.Settings.Default.ExporterWidth = Width;
                Properties.Settings.Default.ExporterMaximized = false;
            }

            Properties.Settings.Default.Save();
        }

        void SetupWindow()
        {
            Top = Properties.Settings.Default.ExporterTop;
            Left = Properties.Settings.Default.ExporterLeft;
            Height = Properties.Settings.Default.ExporterHeight;
            Width = Properties.Settings.Default.ExporterWidth;
            if (Properties.Settings.Default.ExporterMaximized)
            {
                WindowState = WindowState.Maximized;
            }
        }

        void window_Activated(object sender, EventArgs e)
        {
            DCCAssetExporterVM vm = DataContext as DCCAssetExporterVM;
            vm.WindowActivatedCall();
        }

        void window_Deactivated(object sender, EventArgs e)
        {
            DCCAssetExporterVM vm = DataContext as DCCAssetExporterVM;
            vm.WindowsDeactivatedCall();
        }

        void SetupDataContext()
        {
            SetupDataContext(null);
        }

        void SetupDataContext(Process parent)
        {
            DCCAssetExporterVM vm = new DCCAssetExporterVM();
            DataContext = vm;
            if (vm.CloseAction == null)
            {
                vm.CloseAction = new Action(Close);
            }
            vm.ParentProcess = parent;
        }

        protected override void OnClosed(EventArgs e)
        {
            base.OnClosed(e);
            DCCAssetExporterVM vm = DataContext as DCCAssetExporterVM;
            vm.Close();
        }
    }
}

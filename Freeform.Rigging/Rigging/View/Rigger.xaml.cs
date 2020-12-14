namespace Freeform.Rigging
{
    using System;
    using System.Windows;
    using System.Diagnostics;
    using System.Windows.Interop;

    /// <summary>
    /// Interaction logic for Rigger.xaml
    /// </summary>
    public partial class Rigger : Window
    {
        public Rigger()
        {
            InitializeComponent();
            SetupWindow();
            SetupDataContext();
        }

        private void Rigger_Closing(object sender, System.ComponentModel.CancelEventArgs e)
        {
            if (WindowState == WindowState.Maximized)
            {
                // Use the RestoreBounds as the current values will be 0, 0 and the size of the screen
                Properties.Settings.Default.RiggerTop = RestoreBounds.Top;
                Properties.Settings.Default.RiggerLeft = RestoreBounds.Left;
                Properties.Settings.Default.RiggerHeight = RestoreBounds.Height;
                Properties.Settings.Default.RiggerWidth = RestoreBounds.Width;
                Properties.Settings.Default.RiggerMaximized = true;
            }
            else
            {
                Properties.Settings.Default.RiggerTop = Top;
                Properties.Settings.Default.RiggerLeft = Left;
                Properties.Settings.Default.RiggerHeight = Height;
                Properties.Settings.Default.RiggerWidth = Width;
                Properties.Settings.Default.RiggerMaximized = false;
            }

            Properties.Settings.Default.Save();
        }

        public Rigger(Process parent)
        {
            InitializeComponent();

            WindowInteropHelper helper = new WindowInteropHelper(this);
            helper.Owner = parent.MainWindowHandle;

            SetupWindow();
            SetupDataContext();
        }

        void SetupWindow()
        {
            Top = Properties.Settings.Default.RiggerTop;
            Left = Properties.Settings.Default.RiggerLeft;
            Height = Properties.Settings.Default.RiggerHeight;
            Width = Properties.Settings.Default.RiggerWidth;
            if (Properties.Settings.Default.RiggerMaximized)
            {
                WindowState = WindowState.Maximized;
            }
        }

        void SetupDataContext()
        {
            RiggerVM vm = new RiggerVM();
            DataContext = vm;
            if (vm.CloseAction == null)
            {
                vm.CloseAction = new Action(Close);
            }
        }

        protected override void OnClosed(EventArgs e)
        {
            base.OnClosed(e);
            RiggerVM vm = DataContext as RiggerVM;
            vm.Close();
        }

        void window_Deactivated(object sender, EventArgs e)
        {
            RiggerVM vm = DataContext as RiggerVM;
            vm.WindowsDeactivatedCall();
        }
    }
}

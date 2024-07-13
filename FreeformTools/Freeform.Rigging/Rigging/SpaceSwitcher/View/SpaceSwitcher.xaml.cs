namespace Freeform.Rigging.SpaceSwitcher
{
    using System;
    using System.ComponentModel;
    using System.Diagnostics;
    using System.Windows;
    using System.Windows.Interop;

    using Freeform.Core.UI;

    /// <summary>
    /// Interaction logic for RegionEditor.xaml
    /// </summary>
    public partial class SpaceSwitcher : Window
    {
        public SpaceSwitcher()
        {
            InitializeComponent();
            SetupDataContext();
        }

        public SpaceSwitcher(Process parent)
        {
            InitializeComponent();

            WindowInteropHelper helper = new WindowInteropHelper(this);
            helper.Owner = parent.MainWindowHandle;

            SetupDataContext();
        }

        void SetupDataContext()
        {
            SpaceSwitcherVM vm = new SpaceSwitcherVM();
            DataContext = vm;
            if (vm.CloseAction == null)
            {
                vm.CloseAction = new Action(Close);
            }
        }

        protected override void OnClosed(EventArgs e)
        {
            base.OnClosed(e);
            SpaceSwitcherVM vm = DataContext as SpaceSwitcherVM;
            vm.Close();
        }
    }
}

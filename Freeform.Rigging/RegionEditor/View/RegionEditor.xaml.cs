namespace Freeform.Rigging.RegionEditor
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
    public partial class RegionEditor : Window
    {
        public RegionEditor()
        {
            InitializeComponent();
            SetupDataContext();
        }

        public RegionEditor(Process parent)
        {
            InitializeComponent();

            WindowInteropHelper helper = new WindowInteropHelper(this);
            helper.Owner = parent.MainWindowHandle;

            SetupDataContext();
        }

        void SetupDataContext()
        {
            RegionEditorVM vm = new RegionEditorVM();
            DataContext = vm;
            if (vm.CloseAction == null)
            {
                vm.CloseAction = new Action(Close);
            }
        }

        protected override void OnClosed(EventArgs e)
        {
            base.OnClosed(e);
            RegionEditorVM vm = DataContext as RegionEditorVM;
            vm.Close();
        }
    }
}

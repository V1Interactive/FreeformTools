namespace Freeform.Rigging.AnimMirror
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
    public partial class AnimMirror : Window
    {
        public AnimMirror()
        {
            InitializeComponent();
            SetupDataContext();
        }

        public AnimMirror(Process parent)
        {
            InitializeComponent();

            WindowInteropHelper helper = new WindowInteropHelper(this);
            helper.Owner = parent.MainWindowHandle;

            SetupDataContext();
        }

        void SetupDataContext()
        {
            AnimMirrorVM vm = new AnimMirrorVM();
            DataContext = vm;
            if (vm.CloseAction == null)
            {
                vm.CloseAction = new Action(Close);
            }
        }

        protected override void OnClosed(EventArgs e)
        {
            base.OnClosed(e);
            AnimMirrorVM vm = DataContext as AnimMirrorVM;
            vm.Close();
        }
    }
}

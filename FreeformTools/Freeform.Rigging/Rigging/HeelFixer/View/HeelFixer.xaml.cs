namespace Freeform.Rigging.HeelFixer
{
    using System;
    using System.ComponentModel;
    using System.Diagnostics;
    using System.Windows;
    using System.Windows.Interop;

    using Freeform.Core.UI;

    /// <summary>
    /// Interaction logic for HeelFixer.xaml
    /// </summary>
    public partial class HeelFixer : Window
    {
        public HeelFixer()
        {
            InitializeComponent();
            SetupDataContext();
        }

        public HeelFixer(Process parent)
        {
            InitializeComponent();

            WindowInteropHelper helper = new WindowInteropHelper(this);
            helper.Owner = parent.MainWindowHandle;

            SetupDataContext();
        }

        void SetupDataContext()
        {
            HeelFixerVM vm = new HeelFixerVM();
            DataContext = vm;
            if (vm.CloseAction == null)
            {
                vm.CloseAction = new Action(Close);
            }
        }

        protected override void OnClosed(EventArgs e)
        {
            base.OnClosed(e);
            HeelFixerVM vm = DataContext as HeelFixerVM;
            vm.Close();
        }
    }
}
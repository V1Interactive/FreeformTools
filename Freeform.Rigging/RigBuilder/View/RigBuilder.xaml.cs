namespace Freeform.Rigging.RigBuilder
{
    using System;
    using System.Windows;
    using System.Diagnostics;
    using System.Windows.Interop;

    /// <summary>
    /// Interaction logic for RigBuilder.xaml
    /// </summary>
    public partial class RigBuilder : Window
    {
        public RigBuilder()
        {
            InitializeComponent();
        }

        public RigBuilder(Process parent)
        {
            InitializeComponent();

            WindowInteropHelper helper = new WindowInteropHelper(this);
            helper.Owner = parent.MainWindowHandle;

            SetupDataContext();
        }
        void SetupDataContext()
        {
            RigBuilderVM vm = new RigBuilderVM();
            DataContext = vm;
            if (vm.CloseAction == null)
            {
                vm.CloseAction = new Action(Close);
            }
        }

        protected override void OnClosed(EventArgs e)
        {
            base.OnClosed(e);
            RigBuilderVM vm = DataContext as RigBuilderVM;
            vm.Close();
        }
    }
}
